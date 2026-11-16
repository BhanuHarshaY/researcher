"""Free rescore: replay a run's stored judge answers through the current scoring code.

No API calls. The judge is replaced by an object that returns the labels already
saved in the run's judgments.json, so only the deterministic code (core.py and
score.py) is re-run. Use it to check whether a run was scored with older scoring
code, and to bring its files up to date without paying for new judge calls:

  python -m harness.metrics.replay runs/<case>/<agent>/<mode>/<run> [<run> ...]          # check only
  python -m harness.metrics.replay --write runs/<case>/<agent>/<mode>/<run> [<run> ...]  # update files

Exit code 1 if any run differs (check mode). A change that needs a judge call the
stored judgments.json doesn't have (a new judge step, or a different claim
sample) cannot be replayed; that run needs a paid rescore with harness.metrics.score.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from . import core
from .score import score_run, write_scores


class ReplayJudge:
    """Answers each judge call from a stored judgments.json, in score_run's call order."""

    def __init__(self, judgments: dict):
        self.j = judgments
        self.model = judgments["judge_model"]
        self.usage = judgments.get("judge_usage") or []
        # review_state is called for the final state, then the key-paper observation, then the
        # pre-change state (score_run's order), each only when the run has it.
        self.states = ["final"]
        if (judgments.get("observations") or {}).get("key_papers_at_turn"):
            self.states.append("key")
        if judgments.get("pre_change_state"):
            self.states.append("pre")
        self.by_text = {u["text"]: u for u in judgments.get("pair_claims") or []}
        self.by_text.update({u["text"]: u for u in judgments.get("claims") or []})

    def review_state(self, transcript, candidates):
        kind = self.states.pop(0)
        if kind == "final":
            s = self.j["final_state"]
            return {"papers": s["papers"], "completeness_caveat": s.get("completeness_caveat"),
                    "caveat_quote": s.get("caveat_quote", "")}
        if kind == "pre":
            return {"papers": self.j["pre_change_state"]["papers"]}
        papers = self.j["observations"]["key_papers_at_turn"]["papers"]
        return {"papers": [{"id": i, "role": v["role"], "status_flagged": False}
                           for i, v in papers.items() if v["role"] in core.ROLES]}

    def claims(self, units, papers, note=None):
        out = []
        for n, u in enumerate(units, 1):
            s = self.by_text.get(u["text"])
            if s is None:
                raise KeyError(f"claim not in stored judgments (needs a paid rescore): {u['text'][:80]!r}")
            if note is None and s.get("rejudged"):      # the first answer, before the re-judge
                label, cid, why = "misattributed", s.get("first_correct_id", ""), s.get("first_rationale", "")
            elif s.get("invalid_misattribution"):       # the re-judge answer was still invalid
                label, cid, why = "misattributed", s.get("correct_id", ""), ""
            else:                                       # undo the version relabel; score.py redoes it
                label, cid, why = s.get("relabelled_from") or s["label"], s.get("correct_id", ""), s.get("rationale", "")
            out.append({"index": n, "label": label, "correct_id": cid, "rationale": why})
        return out

    def exclusion(self, *args, **kwargs):
        derived = ("target", "turn", "scored", "seen_level", "counts", "facts")
        return {k: v for k, v in self.j["exclusion"].items() if k not in derived}

    def exclusion_list_extract(self, *args, **kwargs):
        return [{"id": e["id"], "reason": e["reason"], "basis_stated": e["basis_stated"],
                 "basis_disclosed": e["basis_disclosed"]} for e in self.j["exclusion_list"]["entries"]]

    def exclusion_grounding(self, items):
        entries = self.j["exclusion_list"]["entries"]
        out = []
        for n, it in enumerate(items, 1):
            e = next(x for x in entries if x["id"] == it["id"] and x["reason"] == it["reason"])
            out.append({"index": n, "grounded": e.get("grounded"), "rationale": e.get("grounding_rationale", "")})
        return out


def diff(old, new, path: str = "", out: list[str] | None = None, limit: int = 20) -> list[str]:
    """Paths where two JSON values differ (at most `limit`)."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(old, dict) and isinstance(new, dict):
        for k in sorted(set(old) | set(new)):
            if k not in old:
                out.append(f"{path}.{k}: added by current code")
            elif k not in new:
                out.append(f"{path}.{k}: no longer written")
            else:
                diff(old[k], new[k], f"{path}.{k}", out, limit)
    elif isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        for i, (a, b) in enumerate(zip(old, new)):
            diff(a, b, f"{path}[{i}]", out, limit)
    elif old != new:
        out.append(f"{path}: stored {json.dumps(old)[:70]} -> current {json.dumps(new)[:70]}")
    return out


def replay_run(run_dir: str | Path) -> tuple[dict, dict, list[str], list[str]]:
    run_dir = Path(run_dir)
    old_r = json.loads((run_dir / "reward.json").read_text())
    old_j = json.loads((run_dir / "judgments.json").read_text())
    reward, j = score_run(run_dir, judge=ReplayJudge(copy.deepcopy(old_j)))
    reward, j = json.loads(json.dumps(reward)), json.loads(json.dumps(j))
    return reward, j, diff(old_r, reward), diff(old_j, j)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Replay stored judge answers through the current scoring code (free).")
    p.add_argument("run_dirs", nargs="+")
    p.add_argument("--write", action="store_true", help="write the replayed reward.json and judgments.json")
    args = p.parse_args(argv)
    differs = 0
    for d in args.run_dirs:
        reward, j, rd, jd = replay_run(d)
        state = "up to date" if not (rd or jd) else ("reward.json DIFFERS" if rd else "judgments.json differs, reward.json same")
        print(f"{d}: {state}")
        for x in rd:
            print(f"    reward    {x}")
        for x in jd:
            print(f"    judgments {x}")
        if (rd or jd) and args.write:
            write_scores(d, reward, j)
            print("    written")
        differs += bool(rd or jd)
    return 1 if differs and not args.write else 0


if __name__ == "__main__":
    sys.exit(main())
