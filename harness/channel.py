"""Chat channel shared by the simulated user and the human user.

One interface: user.next_message(agent_message) -> str | None.
None means the user is done. Both user types implement it, so the agent sees
exactly the same channel in sim and human mode.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

DONE = "/done"


class User(ABC):
    source: str = "user"  # recorded on each user_message event ("sim" | "human")

    @abstractmethod
    def next_message(self, agent_message: str | None) -> str | None:
        """Return the next user message, or None when finished.

        agent_message is None on the very first call (no agent reply yet).
        """

    def close(self, agent_message: str | None) -> None:
        """Called once when the conversation ends because the turn cap was hit."""


class Agent(ABC):
    @abstractmethod
    def respond(self, user_message: str, turn: int) -> str:
        """Handle one user turn (including any tool loop) and return the reply text."""


def is_done(msg: str | None) -> bool:
    return msg is None or msg.strip().lower().startswith(DONE)


def run_conversation(agent: Agent, user: User, recorder, max_user_turns: int) -> None:
    agent_message: str | None = None
    for turn in range(1, max_user_turns + 1):
        msg = user.next_message(agent_message)
        if is_done(msg):
            recorder.event("user_done", after_turn=turn - 1)
            return
        recorder.user_message(msg, turn=turn, source=user.source)
        agent_message = agent.respond(msg, turn=turn)
        recorder.agent_message(agent_message, turn=turn)
    recorder.event("max_user_turns_reached", max_user_turns=max_user_turns)
    user.close(agent_message)
