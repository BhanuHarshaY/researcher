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
import sys
from datetime import datetime
from pathlib import Path

import yaml

from ..config import CASES_DIR, load_models
from ..tools.mock_search import BM25, MockSearch
from . import core
from .judge import Judge, format_transcript
from .names import COST_METRICS

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
    out = judge.review_state(format_transcript(turns), candidates)
    roles = {i: "mentioned" for i in ids}
    flagged = {i: False for i in ids}
    kept = []
    for p in out:
        if p.get("id") in roles and p.get("role") in core.ROLES:
            roles[p["id"]] = p["role"]
            flagged[p["id"]] = bool(p.get("status_flagged"))
            kept.append(p)
    return roles, flagged, {"upto_turn": upto, "papers": kept,
                            "defaulted_to_mentioned": [i for i in ids if i not in {p["id"] for p in kept}]}


def _claim_context(tools: MockSearch, units: list[dict]) -> list[dict]:
    """Cited papers plus the top BM25 neighbours of each claim (to detect misattribution)."""
    full = BM25({
        pid: " ".join([p.get("title", ""), p.get("abstract", "")]
                      + [ps.get("text", "") for ps in p.get("passages") or []])
        for pid, p in tools.papers.items()
    })
    ids: list[str] = []
    for u in units:
        ids += [i for i in u["cited_ids"] if i not in ids]
    for u in units:
        extra = [pid for _s, pid in full.rank(u["text"]) if pid not in u["cited_ids"]]
        ids += [i for i in extra[:MISATTRIBUTION_CANDIDATES] if i not in ids]
    return [tools.papers[i] for i in ids[:MAX_CONTEXT_PAPERS]]


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
    tools = MockSearch(case_dir / "corpus" / "papers.jsonl")
    corpus_ids = set(tools.papers)

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
    final_roles = flagged = pre_roles = claim_labels = explained = None

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

    # 2. Paper set just before the scripted criteria change (if the run reached it).
    ch = fu["criteria_change"]
    reached = ch and any(t["turn"] == ch["user_turn"] and t["agent"] for t in conv)
    if reached and case.get("post_change_expected_ids"):
        res = attempt("pre_change_state", lambda: _review_state(judge, tools, conv, ch["user_turn"] - 1))
        if res:
            pre_roles, _, j["pre_change_state"] = res

    # 3. Claim support (max 15 statements, deterministic selection).
    units = core.claim_units([(t["turn"], t["agent"]) for t in conv if t["agent"]], tools.find_ids)
    j["claims"] = [{**u} for u in units]
    if units:
        out = attempt("claims", lambda: judge.claims(units, _claim_context(tools, units)))
        if out is not None:
            by_index = {c.get("index"): c for c in out}
            for i, u in enumerate(j["claims"], 1):
                c = by_index.get(i, {})
                u.update(label=c.get("label", "not_a_claim"), correct_id=c.get("correct_id", ""),
                         rationale=c.get("rationale", "missing from judge output"))
            mask = core.counted_claims([u["label"] for u in j["claims"]])
            for u, use in zip(j["claims"], mask):
                u["counted"] = use
            claim_labels = [u["label"] for u in j["claims"] if u["counted"]]
    else:
        claim_labels = []

    # 4. "Why didn't you include X?" explanation.
    why = fu["why_excluded"]
    if why and why["target"] in corpus_ids:
        turn = next((t for t in conv if t["turn"] == why["user_turn"] and t["agent"]), None)
        if turn:
            facts = _exclusion_facts(tools, events, conv, why["target"], why["user_turn"])
            out = attempt("exclusion", lambda: judge.exclusion(
                case.get("criteria") or [], tools.papers[why["target"]], facts, turn["user"], turn["agent"]))
            if out is not None:
                explained = int(out.get("verdict") == "explained")
                j["exclusion"] = {"target": why["target"], "turn": why["user_turn"], "facts": facts, **out}

    reward = core.compute_reward(
        case, corpus_ids, final_roles=final_roles, flagged=flagged, pre_roles=pre_roles,
        claim_labels=claim_labels, exclusion_explained=explained, cost=cost,
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
