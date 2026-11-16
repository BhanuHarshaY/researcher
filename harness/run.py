"""Entry point.

  python -m harness.run --case case1_systematic_review --mode sim --agent baseline --runs 5
  python -m harness.run --case case1_systematic_review --mode human --agent baseline

Each run writes runs/<case>/<agent>/<mode>/<UTC timestamp>_<n>/ containing
trajectory.json, reward.json, config.json and judgments.json (judge labels
behind the metrics); in human mode also survey.json and interview_notes.md.
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
from .metrics.score import score_run, write_scores
from .recorder import Recorder, git_commit, now_iso, null_reward, sha256_file
from .survey.survey import run_survey, write_interview_template
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


def sim_progress(run_index: int):
    """Sim mode: one line when each user turn starts and when the agent replies."""
    state = {"t0": time.monotonic(), "calls": 0}

    def show(ev: dict) -> None:
        el = time.monotonic() - state["t0"]
        if ev["type"] == "user_message":
            state["calls"] = 0
            print(f"[run {run_index}] turn {ev['turn']}: user message sent ({el:.0f}s)", flush=True)
        elif ev["type"] == "tool_call":
            state["calls"] += 1
        elif ev["type"] == "agent_message":
            print(f"[run {run_index}] turn {ev['turn']}: agent replied after {state['calls']} tool calls "
                  f"({el:.0f}s)", flush=True)
        elif ev["type"] in ("user_done", "max_user_turns_reached", "error"):
            print(f"[run {run_index}] {ev['type']} ({el:.0f}s)", flush=True)
    return show


def run_one(args, models: dict, case: dict, run_index: int) -> bool:
    started = datetime.now(timezone.utc)
    run_dir = (
        RUNS_DIR / args.case / args.agent / args.mode
        / f"{started.strftime('%Y%m%dT%H%M%SZ')}_{run_index}"
    )
    recorder = Recorder(run_dir, on_event=progress_printer if args.mode == "human" else sim_progress(run_index))
    tools = MockSearch(case["corpus_path"])

    # Build the agent before creating the folder: the proposed stub fails here.
    agent = AGENTS[args.agent](models["agent_model"], tools, recorder, max_tool_calls=MAX_TOOL_CALLS)

    if args.mode == "sim":
        user = SimUser(
            case["spec"], case["persona"], tools.papers, models["sim_user_model"], recorder,
            max_user_turns=MAX_USER_TURNS, find_ids=tools.find_ids,
        )
    else:
        user = HumanUser(case["spec"])

    recorder.create_dir()
    config = {
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
    recorder.write_config(config)

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
        # Written first so the trajectory is on disk even if the survey or scoring fails.
        cost = recorder.cost_metrics(time.monotonic() - t0)
        recorder.event("run_end", ok=ok, ended_at=now_iso())
        recorder.write_trajectory()
        reward = null_reward()
        reward.update(cost)
        recorder.write_reward(reward)
        print(f"[run {run_index}] {'done' if ok else 'FAILED'}: {recorder.run_dir}", flush=True)

    # Failed runs keep null quality metrics (scoring a broken conversation would mislead).
    if ok and args.mode == "human":
        survey = run_survey(recorder.run_dir)
        write_interview_template(recorder.run_dir, config, survey.get("participant_id"))
    if ok and not args.no_score:
        print(f"[run {run_index}] scoring with judge model {models['judge_model']}...", flush=True)
        try:
            reward, judgments = score_run(recorder.run_dir, cost=cost, case_dir=case["dir"])
            write_scores(recorder.run_dir, reward, judgments)
            for err in judgments["errors"]:
                print(f"[run {run_index}] judge error in {err['step']}: {err['error']}", file=sys.stderr)
            flags = [k for k, v in reward.items() if k.startswith("bd_") and v == 1]
            print(f"[run {run_index}] scored. breakdowns: {', '.join(flags) or 'none'}", flush=True)
        except Exception as e:
            print(f"[run {run_index}] SCORING FAILED ({type(e).__name__}: {e}). "
                  f"Rescore later: python -m harness.metrics.score {recorder.run_dir}", file=sys.stderr)
    return ok


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Run a lit-review test case.")
    p.add_argument("--case", required=True, help="case folder name under cases/")
    p.add_argument("--mode", choices=["sim", "human"], required=True)
    p.add_argument("--agent", choices=sorted(AGENTS), default="baseline")
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--start-index", type=int, default=1,
                   help="run_index of the first run (to add runs to an existing set, or run them in parallel)")
    p.add_argument("--no-score", action="store_true",
                   help="skip the judge; quality metrics stay null (rescore later with harness.metrics.score)")
    args = p.parse_args(argv)

    if args.mode == "human" and args.runs != 1:
        p.error("human mode runs one session at a time (--runs 1)")

    models = load_models()
    case = load_case(args.case)

    failures = 0
    for i in range(args.start_index, args.start_index + args.runs):
        try:
            ok = run_one(args, models, case, i)
        except NotImplementedError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        failures += 0 if ok else 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
