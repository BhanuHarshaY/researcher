"""Writes one output folder per run: trajectory.json, reward.json, config.json."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import REPO_ROOT
from .metrics.names import BREAKDOWN_FLAGS, COST_METRICS, QUALITY_METRICS, null_reward  # noqa: F401

TOOL_RESULT_MAX_CHARS = 4000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


class Recorder:
    def __init__(self, run_dir: str | Path, on_event=None):
        # The folder is created by create_dir(), after the agent is built, so a
        # run that fails at setup (e.g. --agent proposed) leaves no empty folder.
        self.run_dir = Path(run_dir)
        self.on_event = on_event  # optional live callback (human-mode progress)
        self.events: list[dict] = []
        # Cost counters (agent only; the sim user's tokens are in usage events).
        self.user_turns = 0
        self.tool_calls = 0
        self.agent_input_tokens = 0
        self.agent_output_tokens = 0

    def create_dir(self) -> None:
        # Two runs starting in the same second with the same index would collide:
        # add a suffix instead of overwriting.
        base, k = self.run_dir, 1
        while True:
            try:
                self.run_dir.mkdir(parents=True, exist_ok=False)
                return
            except FileExistsError:
                k += 1
                self.run_dir = base.with_name(f"{base.name}-{k}")

    def event(self, type_: str, **data) -> dict:
        ev = {"type": type_, "ts": now_iso(), **data}
        self.events.append(ev)
        if self.on_event is not None:
            self.on_event(ev)
        return ev

    # Convenience wrappers so the event schema stays consistent.
    def user_message(self, text: str, turn: int, source: str) -> None:
        self.user_turns = turn
        self.event("user_message", turn=turn, source=source, text=text)

    def agent_message(self, text: str, turn: int) -> None:
        self.event("agent_message", turn=turn, text=text)

    def tool_call(self, name: str, tool_input: dict, tool_use_id: str, turn: int) -> None:
        self.tool_calls += 1
        self.event("tool_call", turn=turn, name=name, input=tool_input, tool_use_id=tool_use_id)

    def tool_result(self, tool_use_id: str, content: str, is_error: bool, turn: int,
                    paper_ids: list[str] | None = None) -> None:
        # paper_ids: corpus ids found in the FULL result, before truncation. The
        # metrics use them to tell which papers the agent actually saw.
        self.event(
            "tool_result",
            turn=turn,
            tool_use_id=tool_use_id,
            is_error=is_error,
            content=content[:TOOL_RESULT_MAX_CHARS],
            truncated=len(content) > TOOL_RESULT_MAX_CHARS,
            original_chars=len(content),
            paper_ids=paper_ids or [],
        )

    def usage(self, role: str, model: str, response, turn: int | None = None) -> None:
        u = response.usage
        cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(u, "cache_creation_input_tokens", 0) or 0
        total_in = (u.input_tokens or 0) + cache_read + cache_write
        if role == "agent":
            self.agent_input_tokens += total_in
            self.agent_output_tokens += u.output_tokens or 0
        self.event(
            "usage",
            role=role,
            turn=turn,
            model=model,
            response_model=getattr(response, "model", None),
            request_id=getattr(response, "_request_id", None),
            stop_reason=response.stop_reason,
            input_tokens=u.input_tokens,
            cache_read_input_tokens=cache_read,
            cache_creation_input_tokens=cache_write,
            output_tokens=u.output_tokens,
        )

    # ---------- files ----------
    def write_json(self, name: str, obj) -> None:
        with open(self.run_dir / name, "w") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
            f.write("\n")

    def write_config(self, config: dict) -> None:
        self.write_json("config.json", config)

    def cost_metrics(self, wall_time_s: float) -> dict:
        return {
            "user_turns": self.user_turns,
            "tool_calls": self.tool_calls,
            "input_tokens": self.agent_input_tokens,
            "output_tokens": self.agent_output_tokens,
            "wall_time_s": round(wall_time_s, 2),
        }

    def write_trajectory(self) -> None:
        self.write_json("trajectory.json", self.events)

    def write_reward(self, reward: dict) -> None:
        self.write_json("reward.json", reward)
