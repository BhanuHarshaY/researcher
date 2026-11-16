"""Human user in the terminal. Same interface as the simulated user.

Turn 1 automatically sends the case's fixed `initial_prompt` (printed so the
person sees it), so turn 1 is identical across sim and human mode. From turn 2
the person types. A message ends with an empty line. Type /done to finish.
"""
from __future__ import annotations

import sys
import textwrap

from ..channel import DONE, User

RULE = "─" * 72


class HumanUser(User):
    source = "human"

    def __init__(self, case: dict, inp=None, out=None):
        self.case = case
        self.inp = inp or sys.stdin
        self.out = out or sys.stdout
        self.turn = 0

    def _print(self, s: str = "") -> None:
        print(s, file=self.out, flush=True)

    def intro(self) -> None:
        self._print(RULE)
        self._print("LITERATURE REVIEW SESSION")
        self._print(RULE)
        self._print("Your goal:")
        self._print(textwrap.indent(textwrap.fill(self.case["goal"].strip(), 68), "  "))
        self._print()
        self._print("The first message is fixed and is sent for you. After the agent replies,")
        self._print("type your message. Finish a message with an EMPTY line.")
        self._print(f"Type {DONE} (then Enter) when you are finished.")
        self._print(RULE)

    def _read_message(self) -> str | None:
        self._print(f"\nYou (turn {self.turn + 1}; empty line to send, {DONE} to finish):")
        lines: list[str] = []
        while True:
            line = self.inp.readline()
            if line == "":  # EOF
                break
            line = line.rstrip("\n")
            if not lines and line.strip().lower().startswith(DONE):
                return None
            if line.strip() == "":
                if lines:
                    break
                continue  # ignore leading blank lines
            lines.append(line)
        return "\n".join(lines).strip() or None

    def next_message(self, agent_message: str | None) -> str | None:
        if agent_message is None:
            self.intro()
            msg = self.case["initial_prompt"].strip()
            self._print(f"\nYou (turn 1, fixed):\n{msg}\n")
            self._print("[agent is working...]")
            self.turn = 1
            return msg

        self._print(f"\n{RULE}\nAGENT:\n{RULE}\n{agent_message}\n{RULE}")
        msg = self._read_message()
        if msg is None:
            return None
        self.turn += 1
        self._print("[agent is working...]")
        return msg

    def close(self, agent_message: str | None) -> None:
        if agent_message is not None:
            self._print(f"\n{RULE}\nAGENT:\n{RULE}\n{agent_message}\n{RULE}")
        self._print("\n[Maximum number of turns reached. Session finished.]")
