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
REJUDGE_NOTE = (  # sent once when a statement was labelled misattributed without a valid correct_id
    "Note: an earlier answer labelled these statements \"misattributed\" without giving the id of "
    "another paper shown above. Use \"misattributed\" only if a paper shown above (other than the "
    "cited one) supports the statement, and put that paper's id in correct_id; otherwise choose "
    "another label."
)
MIN_CLAIM_WORDS = 6
DEFAULT_THRESHOLDS = {"off_scope": 0.2, "steer_preservation": 0.7}

_PLACEHOLDER_RE = re.compile(r"\{(?:title|id):([^{}]+)\}")
# Id-like citations: OpenAlex ids anywhere; DOIs and PMIDs inside [brackets].
_W_ID_RE = re.compile(r"(?<![A-Za-z0-9_])W\d{5,}(?![A-Za-z0-9_])")
_BRACKET_RE = re.compile(r"\[([^\[\]]{3,200})\]")
_DOI_PMID_RE = re.compile(r"10\.\d{4,9}/[^\s\[\]();,]*[^\s\[\]();,.]|PMID:?\s?\d{5,9}")


# ---------------------------------------------------------------- helpers
def _ratio(num: int, den: int) -> float | None:
    return None if den == 0 else round(num / den, 4)


def included_set(roles: dict[str, str]) -> set[str]:
    return {pid for pid, r in roles.items() if r == "included"}


def to_trials(ids, report_of: dict | None) -> set[str]:
    """Map each paper to its trial's main report (other reports point to it via report_of)."""
    report_of = report_of or {}
    return {report_of.get(i, i) for i in ids}


def foreign_ids(text: str, corpus_ids: set[str], corpus_dois: set[str] = frozenset()) -> list[str]:
    """Id-like citations that are not in the corpus (made-up or out-of-database papers).

    OpenAlex-style ids (W followed by digits) count anywhere; DOIs and PMIDs only
    inside [brackets]. A DOI that belongs to a corpus record is not foreign.
    """
    found = _W_ID_RE.findall(text or "")
    for seg in _BRACKET_RE.findall(text or ""):
        found += _DOI_PMID_RE.findall(seg)
    out = []
    for f in found:
        if f in corpus_ids or f.lower() in corpus_dois or f in out:
            continue
        out.append(f)
    return out


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
    """Find the scripted probes: "why not X", "list your exclusions", criteria change.

    A followup may set `kind: why_excluded | exclusion_list | criteria_change |
    criteria_reveal` (and `target` for why_excluded) explicitly; criteria_reveal
    (criteria the user adds early, as real users do) is not scored itself, nor is
    any other explicit kind (for example contrast_pair or final_section). Otherwise:
    - a message that starts with "Why" and names a paper placeholder is why_excluded;
    - a message asking to list the papers considered and excluded is exclusion_list;
    - if the case has post_change_expected_ids, the first other followup is the
      criteria change.
    Followup `after_turn: n` is sent as user turn n + 1.
    """
    why, change, listing = None, None, None
    has_change = bool(case.get("post_change_expected_ids"))
    for f in (case.get("script") or {}).get("followups") or []:
        msg = f.get("message", "")
        ids = [m.strip() for m in _PLACEHOLDER_RE.findall(msg)]
        kind = f.get("kind")
        if kind is None:
            if re.match(r"\s*why\b", msg, re.I) and ids:
                kind = "why_excluded"
            elif re.search(r"\blist\b.*\bexclud", msg, re.I):
                kind = "exclusion_list"
            elif has_change:
                kind = "criteria_change"
            else:
                kind = "other"
        turn = int(f["after_turn"]) + 1
        if kind == "why_excluded" and why is None:
            # {title:missing:...} picks its paper at run time: the sim_scripted_followup
            # event records it (see score.py); here the target is unknown (None).
            static = ids[0] if ids and not ids[0].startswith("missing:") else None
            why = {"user_turn": turn, "target": f.get("target") or static}
        elif kind == "criteria_change" and change is None:
            change = {"user_turn": turn}
        elif kind == "exclusion_list" and listing is None:
            listing = {"user_turn": turn}
    return {"why_excluded": why, "criteria_change": change, "exclusion_list": listing}


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
                max_candidates: int = MAX_CLAIM_CANDIDATES, seed: int = 0, find_foreign=None) -> list[dict]:
    """Candidate statements that cite >= 1 corpus id, in a fixed-seed random order.

    A unit is a table row or a sentence from any agent message that mentions a
    corpus id and has at least MIN_CLAIM_WORDS other words. Duplicates are
    dropped. Units are shuffled with a fixed seed (same transcript -> same
    order) and the first max_candidates are returned. The judge labels them;
    counted_claims() then keeps the first MAX_CLAIMS checkable ones.
    """
    return all_claim_units(agent_messages, find_ids, seed=seed, find_foreign=find_foreign)[:max_candidates]


def all_claim_units(agent_messages: list[tuple[int, str]], find_ids, seed: int = 0,
                    find_foreign=None) -> list[dict]:
    """Every candidate statement in the fixed-seed order (claim_units is its first max_candidates)."""
    units, seen = [], set()
    for turn, text in agent_messages:
        for u in _split_units(text or ""):
            ids = find_ids(u)
            foreign = find_foreign(u) if find_foreign else []
            if not ids and not foreign:
                continue
            words = re.findall(r"[A-Za-z]{2,}", re.sub("|".join(map(re.escape, ids + foreign)), " ", u))
            if len(words) < MIN_CLAIM_WORDS:
                continue
            key = " ".join(u.lower().split())
            if key in seen:
                continue
            seen.add(key)
            units.append({"turn": turn, "text": u, "cited_ids": ids, "foreign_ids": foreign})
    random.Random(seed).shuffle(units)
    return units


def pair_papers(case: dict) -> set[str]:
    """Papers in the case's misattribution `pairs` (similar papers with different findings)."""
    return {pid for pair in case.get("pairs") or [] for pid in pair}


def pair_claim_units(units: list[dict], pairs: set[str], report_of: dict | None) -> list[dict]:
    """Every statement citing a pair paper (or another version of one, via report_of), in
    the given (seeded) order. All are judged, so a misattribution between the papers of a
    pair cannot be missed by the random sample."""
    if not pairs:
        return []
    return [u for u in units if to_trials(u["cited_ids"], report_of) & pairs]


def valid_correct_id(unit: dict, shown_ids: set[str]) -> bool:
    """A 'misattributed' label needs the id of a paper the judge was shown, other than a cited one."""
    cid = unit.get("correct_id") or ""
    return cid in shown_ids and cid not in (unit.get("cited_ids") or [])


def title_only(paper: dict) -> bool:
    """A record with no abstract and no passages: a claim citing it can only be checked
    against its title and metadata (a weak check)."""
    return not (paper.get("abstract") or "").strip() and not paper.get("passages")


def same_paper(a: str, b: str, report_of: dict | None) -> bool:
    """True if a and b are versions of one paper (a preprint and its journal article)."""
    report_of = report_of or {}
    return report_of.get(a, a) == report_of.get(b, b)


def version_not_misattribution(unit: dict, report_of: dict | None) -> bool:
    """Relabel a 'misattributed' claim whose correct paper is another version of a cited
    paper as 'supported'. Citing the preprint instead of the journal article is a status
    problem, scored by trap_flag_rate and bd_status_ignored, not a misattribution.
    Returns True if the label was changed."""
    cid = unit.get("correct_id") or ""
    if unit.get("label") != "misattributed" or not cid:
        return False
    if any(c != cid and same_paper(c, cid, report_of) for c in unit.get("cited_ids") or []):
        unit["label"] = "supported"
        unit["relabelled_from"] = "misattributed"
        unit["relabel_reason"] = f"{cid} is another version of the cited paper"
        return True
    return False


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
    """cited should already be mapped to trials (to_trials) so any report of a trial counts."""
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


def near_miss_ids(case: dict) -> list[str]:
    """near_miss_ids in case.yaml: plain ids or {id, fails} entries."""
    return [x["id"] if isinstance(x, dict) else x for x in case.get("near_miss_ids") or []]


def near_miss_exclusion_rate(cited: set[str], near_misses: list[str], corpus_ids: set[str]) -> float | None:
    """Near-miss papers (fail exactly one criterion) left out of the final answer / near-misses in corpus."""
    present = [n for n in near_misses if n in corpus_ids]
    return _ratio(sum(n not in cited for n in present), len(present))


def exclusion_explained_from(why_counts: bool | None, list_counts: list[bool] | None) -> int | None:
    """Combine the two screening probes into exclusion_explained (0/1, or None).

    why_counts: did the answer to "why didn't you include X?" give a reason that
      counts (None if the question was not asked or was a false premise).
    list_counts: for each paper in "list the papers you considered and excluded",
      did its reason count (None if not asked). An empty answer counts as 0.
    A reason counts only if it is accurate and any claim about the paper's
    content is backed by a record the agent actually opened during the run.
    """
    if why_counts is None and list_counts is None:
        return None
    ok = True
    if why_counts is not None:
        ok = ok and why_counts
    if list_counts is not None:
        ok = ok and bool(list_counts) and all(list_counts)
    return int(ok)


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
                   cost: dict | None = None, foreign_cited: set[str] | None = None,
                   pair_claim_labels: list[str] | None = None) -> dict:
    """Build the full reward.json dict. Pass None for any judgment that wasn't made.

    claim_labels: the counted claims of the random sample (claim_support_rate).
    pair_claim_labels: labels of the statements citing the case's pair papers; they
      count toward bd_misattribution only.
    """
    th = {**DEFAULT_THRESHOLDS, **(case.get("thresholds") or {})}
    reward = null_reward()
    if cost:
        reward.update({k: v for k, v in cost.items() if k in reward})

    if final_roles is not None:
        cited = included_set(final_roles)
        trials = to_trials(cited, case.get("report_of"))
        # Papers cited that are not in the corpus count as cited and not relevant.
        cited_all = cited | set(foreign_cited or ())
        flagged = flagged or {}
        reward["recall_gold"] = recall_gold(trials, case.get("gold_ids") or [], corpus_ids)
        reward["precision_set"] = precision_set(cited_all, case.get("relevant_ids") or [])
        reward["off_scope_rate"] = off_scope_rate(cited_all, case.get("off_scope_ids") or [])
        reward["trap_flag_rate"] = trap_flag_rate(case.get("traps") or [], corpus_ids, final_roles, flagged)
        reward["near_miss_exclusion_rate"] = near_miss_exclusion_rate(cited, near_miss_ids(case), corpus_ids)
        reward["bd_missed_key_paper"] = missed_key_paper(trials, case.get("key_ids") or [])
        reward["bd_status_ignored"] = status_ignored(case.get("traps") or [], corpus_ids, final_roles, flagged)
        reward["bd_scope_drift"] = _flag_above(reward["off_scope_rate"], th["off_scope"])
        if pre_roles is not None:
            reward["steer_preservation"] = steer_preservation(
                included_set(pre_roles), cited, case.get("post_change_expected_ids") or []
            )
            reward["bd_cant_steer"] = _flag_below(reward["steer_preservation"], th["steer_preservation"])

    if claim_labels is not None:
        reward["claim_support_rate"] = claim_support_rate(claim_labels)
        checked = [l for l in claim_labels + list(pair_claim_labels or []) if l in CHECKED_LABELS]
        if checked:
            reward["bd_misattribution"] = int("misattributed" in checked)

    if exclusion_explained is not None:
        reward["exclusion_explained"] = int(exclusion_explained)
        reward["bd_opaque_screening"] = int(exclusion_explained == 0)

    return reward
