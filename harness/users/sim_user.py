"""LLM simulated user, driven by persona.md plus the script in case.yaml.

- Turn 1 sends `initial_prompt` verbatim.
- After the agent's reply to user turn n, a scripted followup with
  `after_turn: n` is sent (template placeholders {title:ID} / {id:ID} are
  filled from the corpus by the harness, not by the LLM).
- Otherwise the LLM persona decides whether to continue or send /done.
- The sim user never sees the gold set, traps or metrics: only the persona,
  the task goal and the conversation transcript.

No `temperature` / `thinking` / `effort` params are sent (model defaults apply;
see harness/agents/baseline.py for why temperature is not sent).
"""
from __future__ import annotations

import re

import anthropic

from ..channel import DONE, User
from ..config import SIM_USER_MAX_TOKENS

_PLACEHOLDER_RE = re.compile(r"\{(title|id):([^{}]+)\}")

SIM_SYSTEM_TEMPLATE = """You are role-playing a researcher who is talking to an AI research assistant about a literature review. Stay in character as the persona below.

# Persona
{persona}

# Your goal for this conversation
{goal}

# How to reply
- You will be shown the conversation so far. Write ONLY your next message to the assistant, as plain text in the first person.
- No preamble, no quotation marks, no stage directions, no notes about being a simulation.
- Only mention papers by ids or titles that already appeared in the conversation.
- If your goal is met, or you have nothing more that is worth asking, reply with exactly: {done}
"""


def render_template(template: str, papers: dict) -> str:
    def sub(m: re.Match) -> str:
        kind, pid = m.group(1), m.group(2).strip()
        if pid not in papers:
            raise KeyError(f"Script placeholder references unknown paper id {pid!r}")
        return papers[pid]["title"] if kind == "title" else pid

    return _PLACEHOLDER_RE.sub(sub, template)


class SimUser(User):
    source = "sim"

    def __init__(self, case: dict, persona: str, papers: dict, model: str, recorder, max_user_turns: int):
        self.case = case
        self.papers = papers
        self.model = model
        self.recorder = recorder
        self.max_user_turns = max_user_turns
        self.followups = {
            int(f["after_turn"]): f["message"]
            for f in (case.get("script") or {}).get("followups") or []
        }
        # Validate all templates up front so a bad case.yaml fails before any API call.
        for msg in self.followups.values():
            render_template(msg, papers)
        self.system = SIM_SYSTEM_TEMPLATE.format(
            persona=persona.strip(), goal=case["goal"].strip(), done=DONE
        )
        self.client = anthropic.Anthropic(max_retries=5)
        self.transcript: list[tuple[str, str]] = []  # (speaker, text)
        self.turn = 0  # user messages sent so far

    def _send(self, msg: str) -> str:
        self.turn += 1
        self.transcript.append(("Researcher (you)", msg))
        return msg

    def next_message(self, agent_message: str | None) -> str | None:
        if agent_message is not None:
            self.transcript.append(("Assistant", agent_message))

        if self.turn == 0:
            return self._send(self.case["initial_prompt"].strip())

        if self.turn in self.followups:
            msg = render_template(self.followups[self.turn], self.papers)
            self.recorder.event("sim_scripted_followup", after_turn=self.turn)
            return self._send(msg)

        return self._llm_decide()

    def _llm_decide(self) -> str | None:
        remaining = self.max_user_turns - self.turn
        convo = "\n\n".join(f"=== {who} ===\n{text}" for who, text in self.transcript)
        prompt = (
            f"Conversation so far:\n\n{convo}\n\n=== End of conversation ===\n\n"
            f"You can send at most {remaining} more message(s). "
            f"Write your next message to the assistant, or exactly {DONE} if you are finished."
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=SIM_USER_MAX_TOKENS,
            system=self.system,
            messages=[{"role": "user", "content": prompt}],
        )
        self.recorder.usage("sim_user", self.model, response, turn=self.turn + 1)
        text = "\n".join(b.text for b in response.content if b.type == "text").strip()
        text = text.strip('"').strip()
        if response.stop_reason == "refusal" or not text or text.lower().startswith(DONE):
            self.recorder.event(
                "sim_user_decision", decision="done", stop_reason=response.stop_reason, raw=text
            )
            return None
        self.recorder.event("sim_user_decision", decision="continue")
        return self._send(text)
