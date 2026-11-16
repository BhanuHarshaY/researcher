"""Baseline agent modelled on Claude Research.

One fixed free-form system prompt (baseline_prompt.md, frozen), a tool loop
(search, read, follow citations), then a written report citing papers by id.
No screening record, no criteria lock, no approval gates.

API notes (claude-sonnet-5-5, API version 2026-10-21 via anthropic>=2.0):
- No `temperature` is sent: 2026-10-21 rejects sampling params, and the model
  samples only at the default (1.0) anyway. config.json records 1.0.
- No `thinking` / `effort` params: the model's defaults (adaptive thinking,
  effort high) apply, as in Claude Research.
- History is append-only and assistant turns are appended as returned
  (`response.content`), which keeps thinking blocks valid across turns.
- No server-side refusal fallback: it would switch models and break the
  pinned-model rule. Refusals are recorded and end the turn.
- Forced tool_choice (any/tool) is not supported on this model; we only use
  tool_choice "none" to force a written answer once the tool budget is spent.
"""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

from ..channel import Agent
from ..config import AGENT_MAX_TOKENS, MAX_TOOL_CALLS
from ..tools.mock_search import TOOL_DEFS, MockSearch

PROMPT_PATH = Path(__file__).with_name("baseline_prompt.md")

BUDGET_EXHAUSTED_MSG = (
    f"Tool-call limit for this turn reached ({MAX_TOOL_CALLS}). This call was not "
    "executed. Write your response to the researcher now using what you have."
)


class BaselineAgent(Agent):
    name = "baseline"

    def __init__(self, model: str, tools: MockSearch, recorder, max_tool_calls: int = MAX_TOOL_CALLS):
        self.model = model
        self.tools = tools
        self.recorder = recorder
        self.max_tool_calls = max_tool_calls
        self.system_prompt = PROMPT_PATH.read_text().strip()
        self.client = anthropic.Anthropic(max_retries=5)
        self.messages: list[dict] = []

    def _call(self, turn: int, force_text: bool):
        kwargs = dict(
            model=self.model,
            max_tokens=AGENT_MAX_TOKENS,
            system=self.system_prompt,
            tools=TOOL_DEFS,
            messages=self.messages,
            # Auto prompt caching of the growing history: cost only, no output change.
            cache_control={"type": "ephemeral"},
        )
        if force_text:
            kwargs["tool_choice"] = {"type": "none"}
        response = self.client.messages.create(**kwargs)
        self.recorder.usage("agent", self.model, response, turn=turn)
        return response

    def respond(self, user_message: str, turn: int) -> str:
        self.messages.append({"role": "user", "content": user_message})
        calls_this_turn = 0
        force_text = False

        while True:
            response = self._call(turn, force_text)
            if response.content:
                self.messages.append({"role": "assistant", "content": response.content})

            text = "\n\n".join(b.text for b in response.content if b.type == "text").strip()
            tool_uses = [b for b in response.content if b.type == "tool_use"]

            if response.stop_reason == "refusal":
                details = getattr(response, "stop_details", None)
                self.recorder.event(
                    "refusal",
                    turn=turn,
                    category=getattr(details, "category", None),
                    explanation=getattr(details, "explanation", None),
                )
                return text or "[The agent declined to respond.]"

            if response.stop_reason == "max_tokens":
                self.recorder.event("max_tokens_reached", turn=turn)

            if not tool_uses:
                return text

            if text:
                # Text the agent wrote alongside tool calls (not the final reply).
                self.recorder.event("agent_interim_text", turn=turn, text=text)

            if force_text:
                # tool_choice=none should make this unreachable; never loop forever.
                self.recorder.event("tool_use_after_budget", turn=turn, n=len(tool_uses))
                return text

            results = []
            for b in tool_uses:
                if calls_this_turn >= self.max_tool_calls:
                    content, is_error = json.dumps({"error": BUDGET_EXHAUSTED_MSG}), True
                    self.recorder.event(
                        "tool_call_rejected", turn=turn, name=b.name, input=b.input,
                        tool_use_id=b.id, reason="max_tool_calls",
                    )
                else:
                    calls_this_turn += 1
                    self.recorder.tool_call(b.name, b.input, b.id, turn=turn)
                    content, is_error = self.tools.execute(b.name, b.input)
                    self.recorder.tool_result(
                        b.id, content, is_error, turn=turn, paper_ids=self.tools.find_ids(content)
                    )
                results.append(
                    {"type": "tool_result", "tool_use_id": b.id, "content": content, "is_error": is_error}
                )
            # All results for one assistant turn go back in a single user message.
            self.messages.append({"role": "user", "content": results})

            if calls_this_turn >= self.max_tool_calls:
                force_text = True
