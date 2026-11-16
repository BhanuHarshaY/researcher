"""Score a run folder: judge calls (judge.py) + deterministic metrics (core.py).

Called by run.py at the end of each run. Can also rescore existing runs
without re-running the agent (judge calls cost money; the agent is not re-run):

  python -m harness.metrics.score runs/<case>/<agent>/<mode>/<run> [<run> ...]

Writes reward.json and judgments.json (the judge's labels, so every metric can
be audited) into the run folder.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

import yaml

from ..config import CASES_DIR, load_models
from ..tools.mock_search import BM25, SNIPPET_CHARS, MockSearch
from . import core
from .judge import Judge, format_transcript
from .names import COST_METRICS

MAX_GROUNDING_CHECKS = 40      # exclusion-list reasons checked against seen text per run (cost cap)
MISATTRIBUTION_CANDIDATES = 3  # extra similar papers shown to the claim judge per claim
MAX_CONTEXT_PAPERS = 40


def cost_from_events(events: list[dict]) -> dict:
    users = [e["turn"] for e in events if e["type"] == "user_message"]
    agent_usage = [e for e in events if e["type"] == "usage" and e.get("role") == "agent"]
    ts = [datetime.fromisoformat(e["ts"]) for e in events if e.get("ts")]
    return {
        "user_turns": max(users) if users else 0,
        "tool_calls": sum(e["type"] == "tool_call" for e in events),
        "input_tokens": sum((e.get("input_tokens") or 0) + (e.get("cache_read_input_tokens") or 0)
                            + (e.get("cache_creation_input_tokens") or 0) for e in agent_usage),
        "output_tokens": sum(e.get("output_tokens") or 0 for e in agent_usage),
        "wall_time_s": round((max(ts) - min(ts)).total_seconds(), 2) if ts else None,
    }


def _review_state(judge: Judge, tools: MockSearch, conv: list[dict], upto: int | None):
    turns = [t for t in conv if upto is None or t["turn"] <= upto]
    ids: list[str] = []
    for t in turns:
        ids += [i for i in tools.find_ids(t["agent"] or "") if i not in ids]
    if not ids:
        return {}, {}, {"upto_turn": upto, "papers": []}
    candidates = [
        {"id": i, "title": tools.papers[i].get("title", ""), "status": tools.papers[i].get("status")}
        for i in ids
    ]
    res = judge.review_state(format_transcript(turns), candidates)
    out = res.get("papers") or []
    roles = {i: "mentioned" for i in ids}
    flagged = {i: False for i in ids}
    kept = []
    for p in out:
        if p.get("id") in roles and p.get("role") in core.ROLES:
            roles[p["id"]] = p["role"]
            flagged[p["id"]] = bool(p.get("status_flagged"))
            kept.append(p)
    return roles, flagged, {"upto_turn": upto, "papers": kept,
                            "completeness_caveat": bool(res.get("completeness_caveat")),
                            "caveat_quote": res.get("caveat_quote", ""),
                            "defaulted_to_mentioned": [i for i in ids if i not in {p["id"] for p in kept}]}


_LEVEL = {"title": 1, "snippet": 2, "full": 3}


def _seen_views(tools: MockSearch, events: list[dict], upto: int) -> dict[str, str]:
    """For each paper, the most the agent saw of it by the end of turn `upto`:
    "title" (a reference/citation list), "snippet" (a search result) or "full" (get_paper)."""
    calls = {e["tool_use_id"]: e for e in events if e["type"] == "tool_call"}
    best: dict[str, str] = {}
    for e in events:
        if e["type"] != "tool_result" or e.get("is_error") or (e.get("turn") or 0) > upto:
            continue
        call = calls.get(e.get("tool_use_id")) or {}
        name, arg = call.get("name"), (call.get("input") or {}).get("id")
        if name == "get_paper":
            pids, level = ([arg] if arg in tools.papers else []), "full"
        elif name == "search_papers":
            pids, level = e.get("paper_ids") or [], "snippet"
        elif name in ("get_references", "get_citations"):
            pids, level = [i for i in e.get("paper_ids") or [] if i != arg], "title"
        else:
            continue
        for pid in pids:
            if pid in tools.papers and _LEVEL[level] > _LEVEL.get(best.get(pid), 0):
                best[pid] = level
    return best


def _seen_text(p: dict, level: str) -> str:
    """Exactly the information the tools showed at that level (never the status fields)."""
    if level == "title":
        return f"{p['title']} ({p.get('year')})"
    if level == "snippet":
        a = p.get("abstract") or ""
        return f"{p['title']} ({p.get('year')}, {p.get('venue')})\n{a[:SNIPPET_CHARS]}{'...' if len(a) > SNIPPET_CHARS else ''}"
    lines = [p["title"], f"Year: {p.get('year')} | Date: {p.get('date')} | Venue: {p.get('venue')}",
             "Abstract: " + (p.get("abstract") or "")]
    lines += [f"- ({x.get('section')}) {x.get('text')}" for x in p.get("passages") or []]
    return "\n".join(lines)[:8000]


def _claim_context(tools: MockSearch, units: list[dict], pinned: list[str] = ()) -> list[dict]:
    """Cited papers plus the top BM25 neighbours of each claim (to detect misattribution).

    `pinned` papers come first, so they always fit under MAX_CONTEXT_PAPERS: the
    case's pair papers, when a statement cites one, so the judge always sees the
    paper a pair claim may really come from.
    """
    full = BM25({
        pid: " ".join([p.get("title", ""), p.get("abstract", "")]
                      + [ps.get("text", "") for ps in p.get("passages") or []])
        for pid, p in tools.papers.items()
    })
    ids: list[str] = [i for i in pinned if i in tools.papers]
    for u in units:
        ids += [i for i in u["cited_ids"] if i not in ids]
    for u in units:
        extra = [pid for _s, pid in full.rank(u["text"]) if pid not in u["cited_ids"]]
        ids += [i for i in extra[:MISATTRIBUTION_CANDIDATES] if i not in ids]
    return [tools.papers[i] for i in ids[:MAX_CONTEXT_PAPERS]]


CLAIM_FIELDS = ("label", "correct_id", "rationale", "rejudged", "first_correct_id", "first_rationale",
                "invalid_misattribution", "relabelled_from", "relabel_reason")


def _apply_labels(units: list[dict], out: list[dict]) -> None:
    by_index = {c.get("index"): c for c in out}
    for i, u in enumerate(units, 1):
        c = by_index.get(i, {})
        u.update(label=c.get("label", "not_a_claim"), correct_id=c.get("correct_id", ""),
                 rationale=c.get("rationale", "missing from judge output"))


def _judge_claims(judge: Judge, attempt, tools: MockSearch, units: list[dict], pinned: list[str], tag: str) -> None:
    """Label units in place: one judge call, then one re-judge of any 'misattributed' label
    without a valid correct_id (a paper shown to the judge, other than a cited one). A label
    that is still invalid after the re-judge counts as unsupported."""
    if not units:
        return
    context = _claim_context(tools, units, pinned)
    out = attempt(tag, lambda: judge.claims(units, context))
    if out is None:
        return
    _apply_labels(units, out)
    shown = {p["id"] for p in context}
    bad = [u for u in units if u["label"] == "misattributed" and not core.valid_correct_id(u, shown)]
    if not bad:
        return
    for u in bad:
        u.update(rejudged=True, first_correct_id=u["correct_id"], first_rationale=u["rationale"])
    out2 = attempt(tag + "_rejudge", lambda: judge.claims(bad, context, note=core.REJUDGE_NOTE))
    if out2 is not None:
        _apply_labels(bad, out2)
    for u in bad:
        if u["label"] == "misattributed" and not core.valid_correct_id(u, shown):
            u.update(label="unsupported", invalid_misattribution=True,
                     rationale="labelled misattributed twice without naming a paper the judge was shown; "
                               "counted as unsupported")


def _exclusion_facts(tools: MockSearch, events: list[dict], conv: list[dict], target: str,
                     why_turn: int) -> list[str]:
    p = tools.papers[target]
    before = [e for e in events if (e.get("turn") or 0) < why_turn]
    seen = [e for e in before if e["type"] == "tool_result" and target in (e.get("paper_ids") or [])]
    calls = {e["tool_use_id"]: e for e in before if e["type"] == "tool_call"}
    opened = any(e["type"] == "tool_call" and e["name"] == "get_paper"
                 and (e.get("input") or {}).get("id") == target for e in before)
    mentioned = any(target in tools.find_ids(t["agent"] or "") for t in conv if t["turn"] < why_turn)
    citing = tools.get_citations(target)["cited_by"]
    cited = tools.get_references(target)["references"]

    facts = ["The paper is in the assistant's database."]
    if p.get("hidden_from_search"):
        links = []
        if citing:
            links.append("get_references of papers that cite it (" + ", ".join(c["id"] for c in citing) + ")")
        if cited:
            links.append("get_citations of papers it cites (" + ", ".join(c["id"] for c in cited) + ")")
        facts.append("Keyword search cannot find it; it is reachable only through "
                     + (" and ".join(links) or "citation links") + ".")
    else:
        facts.append("Keyword search can find it.")
    if seen:
        first = seen[0]
        via = calls.get(first["tool_use_id"], {}).get("name", "a tool")
        facts.append(f"Before the question, it appeared in the assistant's tool results "
                     f"{len(seen)} time(s) (first in turn {first['turn']}, via {via}).")
    else:
        facts.append("Before the question, it never appeared in any of the assistant's tool results.")
    facts.append(f"Before the question, the assistant {'did' if opened else 'did not'} open its full record "
                 f"with get_paper.")
    facts.append(f"Before the question, the assistant {'did' if mentioned else 'did not'} mention its id "
                 f"in a reply.")
    return facts


def score_run(run_dir: str | Path, judge: Judge | None = None, cost: dict | None = None,
              case_dir: str | Path | None = None) -> tuple[dict, dict]:
    run_dir = Path(run_dir)
    config = json.loads((run_dir / "config.json").read_text())
    events = json.loads((run_dir / "trajectory.json").read_text())
    case_dir = Path(case_dir) if case_dir else CASES_DIR / config["case"]
    case = yaml.safe_load((case_dir / "case.yaml").read_text())
    tools = MockSearch(case_dir / "corpus" / "papers.jsonl", ranking=case.get("search_ranking", "bm25"))
    corpus_ids = set(tools.papers)
    report_of = case.get("report_of") or {}

    if cost is None:
        old = run_dir / "reward.json"
        prev = json.loads(old.read_text()) if old.exists() else {}
        cost = ({k: prev.get(k) for k in COST_METRICS}
                if all(prev.get(k) is not None for k in COST_METRICS) else cost_from_events(events))
    if judge is None:
        judge = Judge(load_models()["judge_model"])

    conv = core.conversation(events)
    fu = core.classify_followups(case)
    j: dict = {"judge_model": judge.model, "followups": fu, "errors": []}
    final_roles = flagged = pre_roles = claim_labels = pair_labels = explained = None

    def attempt(name, fn):
        try:
            return fn()
        except Exception as e:  # a failed judgment leaves its metrics null
            j["errors"].append({"step": name, "error": f"{type(e).__name__}: {e}"})
            return None

    # 1. Final paper set (roles + status flags).
    res = attempt("final_state", lambda: _review_state(judge, tools, conv, None))
    if res:
        final_roles, flagged, j["final_state"] = res

    # 1b. Observation only (no metric): key-paper status at the end of the turn set by
    #     `observe_key_papers_at_turn` in case.yaml, e.g. before a later probe could prompt it.
    key_obs = None
    obs_turn = case.get("observe_key_papers_at_turn")
    if obs_turn and case.get("key_ids") and any(t["turn"] == obs_turn and t["agent"] for t in conv):
        res = attempt("key_papers_at_turn", lambda: _review_state(judge, tools, conv, obs_turn))
        if res:
            roles_t = res[0]
            inc_t = core.to_trials(core.included_set(roles_t), report_of)
            seen_t = _seen_views(tools, events, obs_turn)
            papers_t = {k: {"included": k in inc_t, "role": roles_t.get(k, "not mentioned"),
                            "seen": seen_t.get(k, "never seen")} for k in case["key_ids"]}
            key_obs = {"turn": obs_turn, "all_included": all(v["included"] for v in papers_t.values()),
                       "papers": papers_t}

    # 2. Paper set just before the scripted criteria change (if the run reached it).
    ch = fu["criteria_change"]
    reached = ch and any(t["turn"] == ch["user_turn"] and t["agent"] for t in conv)
    if reached and case.get("post_change_expected_ids"):
        res = attempt("pre_change_state", lambda: _review_state(judge, tools, conv, ch["user_turn"] - 1))
        if res:
            pre_roles, _, j["pre_change_state"] = res

    # 3. Claim support (max 15 statements, deterministic selection). A statement that
    #    cites a paper not in the corpus is unsupported without asking the judge.
    corpus_dois = {(p.get("doi") or "").lower() for p in tools.papers.values() if p.get("doi")}
    find_foreign = lambda text: core.foreign_ids(text, corpus_ids, corpus_dois)
    foreign_cited = sorted({f for t in conv for f in find_foreign(t["agent"] or "")})
    j["foreign_citations"] = foreign_cited
    all_units = core.all_claim_units([(t["turn"], t["agent"]) for t in conv if t["agent"]], tools.find_ids,
                                     find_foreign=find_foreign)
    j["claims"] = [{**u} for u in all_units[:core.MAX_CLAIM_CANDIDATES]]
    # Statements citing the case's pair papers are always judged (up to MAX_PAIR_CLAIMS), in
    # the same seeded order; those already in the sample reuse its label.
    pairs = core.pair_papers(case)
    in_sample = {u["text"] for u in j["claims"]}
    pair_units = [{**u, "in_sample": u["text"] in in_sample}
                  for u in core.pair_claim_units(all_units, pairs, report_of)]
    if pairs:
        j["pair_claims"] = pair_units
    extras = [u for u in pair_units if not u["in_sample"]]
    for u in j["claims"] + extras:
        if u["foreign_ids"]:
            u.update(label="unsupported", correct_id="", rationale="cites a paper that is not in the database")
    # The sample is judged in one call (as before); pair claims outside it in a second call
    # with its own context. Pair papers come first in both contexts when pair claims exist.
    pinned = sorted(pairs) if pair_units else []
    _judge_claims(judge, attempt, tools, [u for u in j["claims"] if not u["foreign_ids"]], pinned, "claims")
    _judge_claims(judge, attempt, tools, [u for u in extras if not u["foreign_ids"]], pinned, "pair_claims")
    # A claim credited to one version of a paper (preprint vs journal article) whose content
    # is in the other version is not a misattribution.
    for u in j["claims"] + extras:
        core.version_not_misattribution(u, report_of)
    by_text = {u["text"]: u for u in j["claims"]}
    for u in pair_units:
        if u["in_sample"]:
            u.update({k: by_text[u["text"]][k] for k in CLAIM_FIELDS if k in by_text[u["text"]]})
    # A claim citing a record with no abstract or passages is checked against its title only.
    for u in j["claims"] + pair_units:
        weak = [c for c in u["cited_ids"] if c in tools.papers and core.title_only(tools.papers[c])]
        if weak:
            u["weak_check"] = "title-only record, weak check: " + ", ".join(weak)
    if all("label" in u for u in j["claims"]):
        # Every statement has a label (from the judge, or "unsupported" for papers outside the corpus).
        mask = core.counted_claims([u["label"] for u in j["claims"]])
        for u, use in zip(j["claims"], mask):
            u["counted"] = use
        claim_labels = [u["label"] for u in j["claims"] if u["counted"]]
        pair_labels = [u["label"] for u in pair_units if "label" in u]
    # Otherwise the claims judge failed: claim_labels stays None and the claim metrics stay null.

    # 4. Screening probes. A reason counts only if (a) everything it says that bears on
    #    a criterion is supported by text the agent actually saw in its tool results
    #    (a search snippet, a reference list entry or an opened record), (b) its
    #    process claims match the run log, and (c) it tells the researcher what the
    #    decision was based on (snippet vs full record).
    why_counts = list_counts = None
    why = fu["why_excluded"]
    if why:
        # Prefer the paper actually asked about (recorded when the followup was sent).
        sent = next((e for e in events if e["type"] == "sim_scripted_followup"
                     and e.get("after_turn") == why["user_turn"] - 1 and e.get("targets")), None)
        if sent:
            why = {**why, "target": sent["targets"][0]}
            fu["why_excluded"] = why
    if why and why["target"] in corpus_ids:
        turn = next((t for t in conv if t["turn"] == why["user_turn"] and t["agent"]), None)
        # Same rule as the sim user's {title:missing:...}: left out = not cited in the
        # agent's reply just before the question.
        prev = next((t for t in conv if t["turn"] == why["user_turn"] - 1), None)
        prev_ids = tools.find_ids((prev or {}).get("agent") or "")
        cited_before = bool(prev) and why["target"] in core.to_trials(prev_ids, case.get("report_of")) | set(prev_ids)
        if turn and cited_before:
            # Every listed paper was already cited, so the question was a false premise.
            j["exclusion"] = {"target": why["target"], "turn": why["user_turn"],
                              "scored": False, "why": "false premise: the paper was already cited"}
        elif turn:
            target = tools.papers[why["target"]]
            level = _seen_views(tools, events, why["user_turn"]).get(why["target"])
            seen_text = _seen_text(target, level) if level else "(The assistant never saw this paper in any tool result.)"
            facts = _exclusion_facts(tools, events, conv, why["target"], why["user_turn"])
            out = attempt("exclusion", lambda: judge.exclusion(
                case.get("criteria") or [], target["title"], level or "never seen", seen_text, facts,
                turn["user"], turn["agent"]))
            if out is not None:
                why_counts = (out.get("reason_type") != "no_reason"
                              and bool(out.get("process_claims_accurate"))
                              and bool(out.get("criterion_claims_grounded"))
                              and (bool(out.get("basis_disclosed")) or out.get("reason_type") == "already_included"))
                j["exclusion"] = {"target": why["target"], "turn": why["user_turn"], "scored": True,
                                  "seen_level": level or "never seen", "counts": why_counts, "facts": facts, **out}

    listing = fu.get("exclusion_list")
    # Only score the list probe when the scripted message was actually sent (sim mode);
    # in human mode the person's turn at that position may be about something else.
    sent_list = listing and any(e["type"] == "sim_scripted_followup" and e.get("after_turn") == listing["user_turn"] - 1
                                for e in events)
    lturn = next((t for t in conv if sent_list and t["turn"] == listing["user_turn"] and t["agent"]), None)
    if lturn:
        upto = listing["user_turn"]
        seen = _seen_views(tools, events, upto)
        ext = attempt("exclusion_extract", lambda: judge.exclusion_list_extract(
            [{"id": i, "title": tools.papers[i]["title"]} for i in seen], lturn["user"], lturn["agent"]))
        if ext is not None:
            entries = []
            for e in ext:
                pid = e.get("id") if e.get("id") in corpus_ids else None
                level = seen.get(pid) if pid else None
                entries.append({"id": pid or e.get("id", ""), "reason": e.get("reason", ""),
                                "basis_stated": e.get("basis_stated", "not_stated"),
                                "basis_disclosed": bool(e.get("basis_disclosed")),
                                "seen_level": level or "never seen",
                                # A reason about a paper the agent never saw cannot be grounded.
                                "grounded": False if not level else None})
            pending = [k for k, x in enumerate(entries) if x["grounded"] is None]
            sample = sorted(random.Random(0).sample(pending, min(MAX_GROUNDING_CHECKS, len(pending))))
            checks_ok = True
            if sample:
                items = [{"id": entries[k]["id"], "reason": entries[k]["reason"], "seen_level": entries[k]["seen_level"],
                          "seen_text": _seen_text(tools.papers[entries[k]["id"]], entries[k]["seen_level"])}
                         for k in sample]
                chk = attempt("exclusion_grounding", lambda: judge.exclusion_grounding(items))
                if chk is None:
                    checks_ok = False
                else:
                    by_index = {c.get("index"): c for c in chk}
                    for n, k in enumerate(sample, 1):
                        c = by_index.get(n, {})
                        entries[k]["grounded"] = bool(c.get("grounded"))
                        entries[k]["grounding_rationale"] = c.get("rationale", "missing from judge output")
            for x in entries:
                x["checked"] = x["grounded"] is not None
                x["counts"] = x["basis_disclosed"] and x["grounded"] is not False
            if checks_ok:
                list_counts = [x["counts"] for x in entries]
            levels: dict[str, int] = {}
            for x in entries:
                levels[x["seen_level"]] = levels.get(x["seen_level"], 0) + 1
            j["exclusion_list"] = {
                "turn": upto, "entries": entries, "n": len(entries),
                "seen_levels": levels,
                "n_never_seen": sum(x["seen_level"] == "never seen" for x in entries),
                "n_grounding_checked": sum(1 for x in entries if x["checked"] and x["seen_level"] != "never seen"),
                "n_ungrounded": sum(x["grounded"] is False for x in entries),
                "n_basis_not_disclosed": sum(not x["basis_disclosed"] for x in entries),
                "n_counted": sum(x["counts"] for x in entries),
                "scored": checks_ok,
            }

    explained = core.exclusion_explained_from(why_counts, list_counts)

    # Observations (not core metrics): eligible trials missed, and whether the agent
    # warned that its list might be incomplete.
    if final_roles is not None:
        inc_trials = core.to_trials(core.included_set(final_roles), case.get("report_of"))
        eligible = core.to_trials(case.get("relevant_ids") or [], case.get("report_of"))
        missed = sorted(eligible - inc_trials)
        j["observations"] = {
            "missed_gold_trials": sorted(set(case.get("gold_ids") or []) - inc_trials),
            "missed_eligible_trials": missed,
            "completeness_caveat": (j.get("final_state") or {}).get("completeness_caveat"),
            "caveat_quote": (j.get("final_state") or {}).get("caveat_quote", ""),
            "missed_eligible_without_warning": bool(missed) and not (j.get("final_state") or {}).get("completeness_caveat"),
        }
    if key_obs:
        j.setdefault("observations", {})["key_papers_at_turn"] = key_obs

    # 5. Trap evidence: did the agent see the evidence for each trap's status? A flag
    #    with no evidence seen suggests knowledge from training data, not from the tools.
    seen_ids = {i for e in events if e["type"] == "tool_result" for i in e.get("paper_ids") or []}
    j["trap_evidence"] = {}
    for t in case.get("traps") or []:
        p = tools.papers.get(t["id"])
        if not p:
            continue
        if t.get("kind") == "retracted":
            notices = [k for k, q in tools.papers.items() if q.get("notice_for") == t["id"]]
            evidence = {"notices": notices, "notice_seen": any(n in seen_ids for n in notices)}
            seen = evidence["notice_seen"]
        else:
            pub = p.get("published_version_id")
            evidence = {"published_version": pub, "published_version_seen": pub in seen_ids}
            seen = evidence["published_version_seen"]
        role = (final_roles or {}).get(t["id"], "not mentioned")
        flag = bool((flagged or {}).get(t["id"]))
        j["trap_evidence"][t["id"]] = {"kind": t.get("kind"), "role": role, "flagged": flag, **evidence,
                                       "flagged_without_seen_evidence": flag and not seen}

    reward = core.compute_reward(
        case, corpus_ids, final_roles=final_roles, flagged=flagged, pre_roles=pre_roles,
        claim_labels=claim_labels, exclusion_explained=explained, cost=cost,
        foreign_cited=set(foreign_cited), pair_claim_labels=pair_labels,
    )
    j["included_ids"] = sorted(core.included_set(final_roles)) if final_roles is not None else None
    j["judge_usage"] = judge.usage
    return reward, j


def write_scores(run_dir: str | Path, reward: dict, judgments: dict) -> None:
    run_dir = Path(run_dir)
    for name, obj in (("reward.json", reward), ("judgments.json", judgments)):
        with open(run_dir / name, "w") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
            f.write("\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="(Re)score run folders with the judge model.")
    p.add_argument("run_dirs", nargs="+")
    args = p.parse_args(argv)
    failed = 0
    for d in args.run_dirs:
        reward, j = score_run(d)
        write_scores(d, reward, j)
        print(f"{d}: errors={len(j['errors'])}")
        print(json.dumps(reward, indent=2))
        failed += bool(j["errors"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
