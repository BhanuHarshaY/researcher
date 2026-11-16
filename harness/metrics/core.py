"""Core objective metrics (CLAUDE.md core metrics table).

Everything here is pure and deterministic: functions take the case spec, the
corpus and already-made judgments (paper roles, claim labels, exclusion
verdict) and return numbers. LLM calls live in judge.py; score.py wires the
two together. Definitions are documented in shared/metrics.md.

Conventions:
- A paper "role" in the review is one of: included | excluded | mentioned.
  "Cited papers" means papers whose role is "included" in the final review.
- A metric is None (null in reward.json) when it doesn't apply or its
  denominator is zero.
"""
from __future__ import annotations

import random
import re

from .names import null_reward

ROLES = ("included", "excluded", "mentioned")
CLAIM_LABELS = ("supported", "unsupported", "misattributed", "not_a_claim")
CHECKED_LABELS = ("supported", "unsupported", "misattributed")
MAX_CLAIMS = 15             # claims counted per run (CLAUDE.md)
MAX_CLAIM_CANDIDATES = 40   # statements sent to the judge to find up to 15 checkable claims
MIN_CLAIM_WORDS = 6
DEFAULT_THRESHOLDS = {"off_scope": 0.2, "steer_preservation": 0.7}

_PLACEHOLDER_RE = re.compile(r"\{(?:title|id):([^{}]+)\}")


# ---------------------------------------------------------------- helpers
def _ratio(num: int, den: int) -> float | None:
    return None if den == 0 else round(num / den, 4)


def included_set(roles: dict[str, str]) -> set[str]:
    return {pid for pid, r in roles.items() if r == "included"}


def conversation(events: list[dict]) -> list[dict]:
    """[{turn, user, agent}] from trajectory events, in turn order."""
    turns: dict[int, dict] = {}
    for e in events:
        if e["type"] == "user_message":
            turns.setdefault(e["turn"], {"turn": e["turn"], "user": None, "agent": None})["user"] = e["text"]
        elif e["type"] == "agent_message":
            turns.setdefault(e["turn"], {"turn": e["turn"], "user": None, "agent": None})["agent"] = e["text"]
    return [turns[t] for t in sorted(turns)]


def classify_followups(case: dict) -> dict:
    """Find which scripted followups are the "why not X" question and the criteria change.

    A followup may set `kind: why_excluded | criteria_change` (and `target` for
    why_excluded) explicitly. Otherwise:
    - a message that starts with "Why" and names a paper placeholder is why_excluded;
    - if the case has post_change_expected_ids, the first other followup is the
      criteria change.
    Followup `after_turn: n` is sent as user turn n + 1.
    """
    why, change = None, None
    has_change = bool(case.get("post_change_expected_ids"))
    for f in (case.get("script") or {}).get("followups") or []:
        msg = f.get("message", "")
        ids = [m.strip() for m in _PLACEHOLDER_RE.findall(msg)]
        kind = f.get("kind")
        if kind is None:
            if re.match(r"\s*why\b", msg, re.I) and ids:
                kind = "why_excluded"
            elif has_change:
                kind = "criteria_change"
            else:
                kind = "other"
        turn = int(f["after_turn"]) + 1
        if kind == "why_excluded" and why is None:
            why = {"user_turn": turn, "target": f.get("target") or (ids[0] if ids else None)}
        elif kind == "criteria_change" and change is None:
            change = {"user_turn": turn}
    return {"why_excluded": why, "criteria_change": change}


# ---------------------------------------------------------------- claim units
def _split_units(text: str) -> list[str]:
    """Markdown table rows and sentences (bullets/paragraphs split on sentence ends)."""
    units = []
    for line in text.splitlines():
        line = line.strip()
        if not line or set(line) <= set("|-: "):
            continue
        if line.startswith("|"):
            units.append(line)
            continue
        line = re.sub(r"^([-*+]|\d+[.)])\s+", "", line)
        units.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\[(*])", line) if s.strip())
    return units


def claim_units(agent_messages: list[tuple[int, str]], find_ids,
                max_candidates: int = MAX_CLAIM_CANDIDATES, seed: int = 0) -> list[dict]:
    """Candidate statements that cite >= 1 corpus id, in a fixed-seed random order.

    A unit is a table row or a sentence from any agent message that mentions a
    corpus id and has at least MIN_CLAIM_WORDS other words. Duplicates are
    dropped. Units are shuffled with a fixed seed (same transcript -> same
    order) and the first max_candidates are returned. The judge labels them;
    counted_claims() then keeps the first MAX_CLAIMS checkable ones.
    """
    units, seen = [], set()
    for turn, text in agent_messages:
        for u in _split_units(text or ""):
            ids = find_ids(u)
            if not ids:
                continue
            words = re.findall(r"[A-Za-z]{2,}", re.sub("|".join(map(re.escape, ids)), " ", u))
            if len(words) < MIN_CLAIM_WORDS:
                continue
            key = " ".join(u.lower().split())
            if key in seen:
                continue
            seen.add(key)
            units.append({"turn": turn, "text": u, "cited_ids": ids})
    random.Random(seed).shuffle(units)
    return units[:max_candidates]


def counted_claims(labels: list[str], max_claims: int = MAX_CLAIMS) -> list[bool]:
    """Mask of labels that count: the first max_claims checkable ones, in candidate order."""
    mask, n = [], 0
    for label in labels:
        use = label in CHECKED_LABELS and n < max_claims
        n += use
        mask.append(use)
    return mask


# ---------------------------------------------------------------- metrics
def recall_gold(cited: set[str], gold_ids: list[str], corpus_ids: set[str]) -> float | None:
    findable = [g for g in gold_ids if g in corpus_ids]
    return _ratio(sum(g in cited for g in findable), len(findable))


def precision_set(cited: set[str], relevant_ids: list[str]) -> float | None:
    return _ratio(len(cited & set(relevant_ids)), len(cited))


def off_scope_rate(cited: set[str], off_scope_ids: list[str]) -> float | None:
    return _ratio(len(cited & set(off_scope_ids)), len(cited))


def claim_support_rate(labels: list[str]) -> float | None:
    checked = [l for l in labels if l in CHECKED_LABELS]
    return _ratio(sum(l == "supported" for l in checked), len(checked))


def _traps_present(traps: list[dict], corpus_ids: set[str]) -> list[dict]:
    return [t for t in traps or [] if t.get("id") in corpus_ids]


def trap_flag_rate(traps: list[dict], corpus_ids: set[str], roles: dict[str, str],
                   flagged: dict[str, bool]) -> float | None:
    """Traps flagged correctly or not cited (excluded / never cited), over traps in the corpus."""
    present = _traps_present(traps, corpus_ids)
    ok = sum(roles.get(t["id"]) != "included" or bool(flagged.get(t["id"])) for t in present)
    return _ratio(ok, len(present))


def status_ignored(traps: list[dict], corpus_ids: set[str], roles: dict[str, str],
                   flagged: dict[str, bool]) -> int | None:
    """1 if a retracted trap or superseded preprint is cited without a flag."""
    present = [t for t in _traps_present(traps, corpus_ids)
               if t.get("kind") in ("retracted", "superseded_preprint")]
    if not present:
        return None
    return int(any(roles.get(t["id"]) == "included" and not flagged.get(t["id"]) for t in present))


def steer_preservation(pre_cited: set[str] | None, post_cited: set[str] | None,
                       expected_ids: list[str]) -> float | None:
    """Kept-and-still-valid papers / papers that should have been kept.

    Should have been kept = cited before the criteria change AND still valid
    under the new criteria (post_change_expected_ids).
    """
    if pre_cited is None or post_cited is None or not expected_ids:
        return None
    should = pre_cited & set(expected_ids)
    return _ratio(len(should & post_cited), len(should))


def missed_key_paper(cited: set[str], key_ids: list[str]) -> int | None:
    if not key_ids:
        return None
    return int(any(k not in cited for k in key_ids))


def _flag_above(value, threshold) -> int | None:
    return None if value is None else int(value > threshold)


def _flag_below(value, threshold) -> int | None:
    return None if value is None else int(value < threshold)


# ---------------------------------------------------------------- reward
def compute_reward(case: dict, corpus_ids: set[str], *, final_roles: dict[str, str] | None,
                   flagged: dict[str, bool] | None, pre_roles: dict[str, str] | None,
                   claim_labels: list[str] | None, exclusion_explained: int | None,
                   cost: dict | None = None) -> dict:
    """Build the full reward.json dict. Pass None for any judgment that wasn't made."""
    th = {**DEFAULT_THRESHOLDS, **(case.get("thresholds") or {})}
    reward = null_reward()
    if cost:
        reward.update({k: v for k, v in cost.items() if k in reward})

    if final_roles is not None:
        cited = included_set(final_roles)
        flagged = flagged or {}
        reward["recall_gold"] = recall_gold(cited, case.get("gold_ids") or [], corpus_ids)
        reward["precision_set"] = precision_set(cited, case.get("relevant_ids") or [])
        reward["off_scope_rate"] = off_scope_rate(cited, case.get("off_scope_ids") or [])
        reward["trap_flag_rate"] = trap_flag_rate(case.get("traps") or [], corpus_ids, final_roles, flagged)
        reward["bd_missed_key_paper"] = missed_key_paper(cited, case.get("key_ids") or [])
        reward["bd_status_ignored"] = status_ignored(case.get("traps") or [], corpus_ids, final_roles, flagged)
        reward["bd_scope_drift"] = _flag_above(reward["off_scope_rate"], th["off_scope"])
        if pre_roles is not None:
            reward["steer_preservation"] = steer_preservation(
                included_set(pre_roles), cited, case.get("post_change_expected_ids") or []
            )
            reward["bd_cant_steer"] = _flag_below(reward["steer_preservation"], th["steer_preservation"])

    if claim_labels is not None:
        reward["claim_support_rate"] = claim_support_rate(claim_labels)
        if any(l in CHECKED_LABELS for l in claim_labels):
            reward["bd_misattribution"] = int("misattributed" in claim_labels)

    if exclusion_explained is not None:
        reward["exclusion_explained"] = int(exclusion_explained)
        reward["bd_opaque_screening"] = int(exclusion_explained == 0)

    return reward
