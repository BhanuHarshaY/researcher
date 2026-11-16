"""Fixed core metric names (CLAUDE.md). Identical across all cases.

Standard library only, so summarize.py can run on the host without installing
anything.
"""

QUALITY_METRICS = [
    "recall_gold",
    "precision_set",
    "off_scope_rate",
    "claim_support_rate",
    "trap_flag_rate",
    "exclusion_explained",
    "steer_preservation",
]
COST_METRICS = ["user_turns", "tool_calls", "input_tokens", "output_tokens", "wall_time_s"]
BREAKDOWN_FLAGS = [
    "bd_scope_drift",
    "bd_missed_key_paper",
    "bd_opaque_screening",
    "bd_cant_steer",
    "bd_misattribution",
    "bd_status_ignored",
]
ALL_METRICS = QUALITY_METRICS + COST_METRICS + BREAKDOWN_FLAGS


def null_reward() -> dict:
    return {k: None for k in ALL_METRICS}
