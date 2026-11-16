"""Shared configuration: repo paths, pinned models, loop limits.

Model names live ONLY in config/models.yaml. Every module that needs a model
name gets it through load_models().
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_PATH = REPO_ROOT / "config" / "models.yaml"
CASES_DIR = REPO_ROOT / "cases"
RUNS_DIR = REPO_ROOT / "runs"

# Loop limits (CLAUDE.md: max 40 tool calls per turn, max 6 user turns).
MAX_TOOL_CALLS = 40
MAX_USER_TURNS = 6

# max_tokens per model call. Non-streaming requests, so stay well under SDK timeouts.
AGENT_MAX_TOKENS = 16000
SIM_USER_MAX_TOKENS = 16000  # includes the sim model's thinking tokens

_REQUIRED_KEYS = ("agent_model", "sim_user_model", "judge_model", "temperature")


def load_models() -> dict:
    with open(MODELS_PATH) as f:
        cfg = yaml.safe_load(f)
    missing = [k for k in _REQUIRED_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"{MODELS_PATH} is missing keys: {missing}")
    return cfg
