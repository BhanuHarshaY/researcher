"""Proposed agent: stub.

The proposed agent is a LangGraph pipeline (locked criteria, query approval
gate, three screeners, paper-set gate, outline-then-draft with claim checks,
append-only log). It is not built yet. When it is, it must use the SAME agent
model (config/models.yaml: agent_model), the SAME tools
(harness/tools/mock_search.py), the SAME chat channel and the SAME metrics as
the baseline. See cases/<case>/DOC.md section 7 for how it would run.
"""
from __future__ import annotations

from ..channel import Agent


class ProposedAgent(Agent):
    name = "proposed"

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "The proposed agent is not implemented yet (planned: LangGraph pipeline with "
            "locked criteria, query approval gate, three screeners, paper-set gate, "
            "outline-then-draft with claim checks, append-only log). "
            "Run with --agent baseline for now. See cases/<case>/DOC.md section 7."
        )

    def respond(self, user_message: str, turn: int) -> str:  # pragma: no cover
        raise NotImplementedError
