"""Aggregate runs of one case/agent/mode into summary.json and summary.md.

  python -m harness.metrics.summarize --case case1_systematic_review
  python -m harness.metrics.summarize --case case1_systematic_review --agent baseline --mode sim --last 5

Reads runs/<case>/<agent>/<mode>/*/reward.json (and judgments.json for the
cited-paper sets). Adds rerun_overlap (mean pairwise Jaccard of cited-paper
sets) and counts how many runs showed each bd_* flag.

Standard library only: runs on the host without installing anything.
"""
from __future__ import annotations

import argparse
import itertools
import json
import statistics
import sys
from pathlib import Path

from .names import BREAKDOWN_FLAGS, COST_METRICS, QUALITY_METRICS

RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def rerun_overlap(sets: list[set]) -> float | None:
    pairs = list(itertools.combinations(sets, 2))
    if not pairs:
        return None
    return round(sum(jaccard(a, b) for a, b in pairs) / len(pairs), 4)


def _stats(values: list) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"mean": None, "sd": None, "min": None, "max": None, "n": 0}
    return {
        "mean": round(statistics.fmean(vals), 4),
        "sd": round(statistics.stdev(vals), 4) if len(vals) > 1 else None,
        "min": min(vals),
        "max": max(vals),
        "n": len(vals),
    }


def load_runs(mode_dir: Path, last: int | None = None) -> list[dict]:
    dirs = sorted(d for d in mode_dir.iterdir() if (d / "reward.json").exists()) if mode_dir.exists() else []
    if last:
        dirs = dirs[-last:]
    runs = []
    for d in dirs:
        j = d / "judgments.json"
        judgments = json.loads(j.read_text()) if j.exists() else {}
        runs.append({
            "name": d.name,
            "reward": json.loads((d / "reward.json").read_text()),
            "included_ids": judgments.get("included_ids"),
        })
    return runs


def summarize(runs: list[dict]) -> dict:
    metrics = {m: _stats([r["reward"].get(m) for r in runs]) for m in QUALITY_METRICS + COST_METRICS}
    breakdowns = {}
    for b in BREAKDOWN_FLAGS:
        vals = [r["reward"].get(b) for r in runs if r["reward"].get(b) is not None]
        breakdowns[b] = {"runs_flagged": sum(v == 1 for v in vals), "n": len(vals)}
    sets = [set(r["included_ids"]) for r in runs if r["included_ids"] is not None]
    return {
        "n_runs": len(runs),
        "runs": [r["name"] for r in runs],
        "metrics": metrics,
        "breakdowns": breakdowns,
        "rerun_overlap": rerun_overlap(sets),
        "rerun_overlap_n": len(sets),
    }


def _fmt(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.3f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))
    return str(v)


def to_markdown(case: str, agent: str, mode: str, s: dict, runs: list[dict]) -> str:
    lines = [f"# Summary: {case} / {agent} / {mode}", "",
             f"Runs: {s['n_runs']} ({', '.join(s['runs'])})", "",
             "## Metrics", "", "| Metric | Mean | SD | Min | Max | n |", "|---|---|---|---|---|---|"]
    for m, st in s["metrics"].items():
        lines.append(f"| `{m}` | {_fmt(st['mean'])} | {_fmt(st['sd'])} | {_fmt(st['min'])} | "
                     f"{_fmt(st['max'])} | {st['n']} |")
    lines.append(f"| `rerun_overlap` | {_fmt(s['rerun_overlap'])} | | | | {s['rerun_overlap_n']} |")
    lines += ["", "## Breakdowns", "", "| Breakdown | Runs flagged |", "|---|---|"]
    for b, c in s["breakdowns"].items():
        lines.append(f"| `{b}` | {c['runs_flagged']} of {c['n']} |" if c["n"] else f"| `{b}` | n/a |")
    cols = QUALITY_METRICS + BREAKDOWN_FLAGS
    lines += ["", "## Per run", "", "| Run | " + " | ".join(f"`{c}`" for c in cols) + " |",
              "|---|" + "---|" * len(cols)]
    for r in runs:
        lines.append(f"| {r['name']} | " + " | ".join(_fmt(r["reward"].get(c)) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Aggregate runs into summary.json + summary.md.")
    p.add_argument("--case", required=True)
    p.add_argument("--agent", default="baseline")
    p.add_argument("--mode", default="sim")
    p.add_argument("--last", type=int, default=None, help="only the N most recent runs")
    args = p.parse_args(argv)

    mode_dir = RUNS_DIR / args.case / args.agent / args.mode
    runs = load_runs(mode_dir, args.last)
    if not runs:
        print(f"No scored runs in {mode_dir}", file=sys.stderr)
        return 1
    s = {"case": args.case, "agent": args.agent, "mode": args.mode, **summarize(runs)}
    (mode_dir / "summary.json").write_text(json.dumps(s, indent=2) + "\n")
    md = to_markdown(args.case, args.agent, args.mode, s, runs)
    (mode_dir / "summary.md").write_text(md)
    print(md)
    print(f"Wrote {mode_dir / 'summary.json'} and {mode_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
