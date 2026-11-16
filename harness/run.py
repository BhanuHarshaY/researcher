"""Entry point.

  python -m harness.run --case case1_systematic_review --mode sim --agent baseline --runs 5
  python -m harness.run --case case1_systematic_review --mode human --agent baseline

Each run writes runs/<case>/<agent>/<mode>/<UTC timestamp>_<n>/ containing
trajectory.json, reward.json and config.json.
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback
from datetime import datetime, timezone
from importlib.metadata import version

import yaml

from .agents.baseline import PROMPT_PATH as BASELINE_PROMPT_PATH
from .agents.baseline import BaselineAgent
from .agents.proposed import ProposedAgent
from .channel import run_conversation
from .config import CASES_DIR, MAX_TOOL_CALLS, MAX_USER_TURNS, RUNS_DIR, load_models
from .recorder import Recorder, git_commit, now_iso, null_reward, sha256_file
from .tools.mock_search import MockSearch
from .users.human_user import HumanUser
from .users.sim_user import SimUser

AGENTS = {"baseline": BaselineAgent, "proposed": ProposedAgent}


def load_case(case_name: str) -> dict:
    case_dir = CASES_DIR / case_name
    if not (case_dir / "case.yaml").exists():
        sys.exit(f"Case not found: {case_dir / 'case.yaml'}")
    with open(case_dir / "case.yaml") as f:
        case = yaml.safe_load(f)
    return {
        "dir": case_dir,
        "spec": case,
        "persona": (case_dir / "persona.md").read_text(),
        "corpus_path": case_dir / "corpus" / "papers.jsonl",
    }


def progress_printer(ev: dict) -> None:
    """Human mode: show tool activity while the agent works (like Claude Research's activity feed)."""
    if ev["type"] == "tool_call":
        args = ", ".join(f"{k}={v!r}" for k, v in ev["input"].items())
        print(f"  · {ev['name']}({args})", file=sys.stderr, flush=True)


def run_one(args, models: dict, case: dict, run_index: int) -> bool:
    started = datetime.now(timezone.utc)
    run_dir = (
        RUNS_DIR / args.case / args.agent / args.mode
        / f"{started.strftime('%Y%m%dT%H%M%SZ')}_{run_index}"
    )
    recorder = Recorder(run_dir, on_event=progress_printer if args.mode == "human" else None)
    tools = MockSearch(case["corpus_path"])

    # Build the agent before creating the folder: the proposed stub fails here.
    agent = AGENTS[args.agent](models["agent_model"], tools, recorder, max_tool_calls=MAX_TOOL_CALLS)

    if args.mode == "sim":
        user = SimUser(
            case["spec"], case["persona"], tools.papers, models["sim_user_model"], recorder,
            max_user_turns=MAX_USER_TURNS,
        )
    else:
        user = HumanUser(case["spec"])

    recorder.create_dir()
    recorder.write_config(
        {
            "case": args.case,
            "mode": args.mode,
            "agent": args.agent,
            "agent_model": models["agent_model"],
            "sim_user_model": models["sim_user_model"],
            "judge_model": models["judge_model"],
            "temperature": models["temperature"],
            "temperature_note": "API default; not sent (API version 2026-10-21 rejects sampling params).",
            "baseline_prompt_sha256": sha256_file(BASELINE_PROMPT_PATH),
            "corpus_sha256": tools.corpus_sha256,
            "case_yaml_sha256": sha256_file(case["dir"] / "case.yaml"),
            "git_commit": git_commit(),
            "anthropic_sdk_version": version("anthropic"),
            "max_tool_calls": MAX_TOOL_CALLS,
            "max_user_turns": MAX_USER_TURNS,
            "started_at": started.isoformat(timespec="seconds"),
            "run_index": run_index,
        }
    )

    t0 = time.monotonic()
    ok = True
    try:
        run_conversation(agent, user, recorder, MAX_USER_TURNS)
    except KeyboardInterrupt:
        recorder.event("interrupted")
        ok = False
        raise
    except Exception as e:  # record, keep the partial trajectory, move on to the next run
        recorder.event("error", error_type=type(e).__name__, message=str(e),
                       traceback=traceback.format_exc())
        print(f"[run {run_index}] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        ok = False
    finally:
        reward = null_reward()  # quality metrics + bd_* flags: filled in Phase 2
        reward.update(recorder.cost_metrics(time.monotonic() - t0))
        recorder.event("run_end", ok=ok, ended_at=now_iso())
        recorder.finalize(reward)
        print(f"[run {run_index}] {'done' if ok else 'FAILED'}: {recorder.run_dir}", flush=True)
    return ok


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Run a lit-review test case.")
    p.add_argument("--case", required=True, help="case folder name under cases/")
    p.add_argument("--mode", choices=["sim", "human"], required=True)
    p.add_argument("--agent", choices=sorted(AGENTS), default="baseline")
    p.add_argument("--runs", type=int, default=1)
    args = p.parse_args(argv)

    if args.mode == "human" and args.runs != 1:
        p.error("human mode runs one session at a time (--runs 1)")

    models = load_models()
    case = load_case(args.case)

    failures = 0
    for i in range(1, args.runs + 1):
        try:
            ok = run_one(args, models, case, i)
        except NotImplementedError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        failures += 0 if ok else 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
