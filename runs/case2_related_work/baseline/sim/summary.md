# Summary: case2_related_work / baseline / sim

Runs: 5 (20261116T223651Z_1, 20261116T223653Z_2, 20261116T223655Z_3, 20261116T223657Z_4, 20261116T223659Z_5)

## Metrics

| Metric | Mean | SD | Min | Max | n |
|---|---|---|---|---|---|
| `recall_gold` | 0.635 | 0.049 | 0.588 | 0.706 | 5 |
| `precision_set` | 0.961 | 0.013 | 0.949 | 0.976 | 5 |
| `off_scope_rate` | 0 | 0 | 0 | 0 | 5 |
| `claim_support_rate` | 0.92 | 0.073 | 0.8 | 1 | 5 |
| `trap_flag_rate` | 1 | 0 | 1 | 1 | 5 |
| `near_miss_exclusion_rate` | n/a | n/a | n/a | n/a | 0 |
| `exclusion_explained` | 0.2 | 0.447 | 0 | 1 | 5 |
| `steer_preservation` | n/a | n/a | n/a | n/a | 0 |
| `user_turns` | 5 | 0 | 5 | 5 | 5 |
| `tool_calls` | 58.4 | 2.302 | 56 | 61 | 5 |
| `input_tokens` | 1274135.6 | 65907.036 | 1214662 | 1372950 | 5 |
| `output_tokens` | 23710.8 | 2510.985 | 20779 | 27001 | 5 |
| `wall_time_s` | 231.3 | 22.279 | 204.54 | 258.22 | 5 |
| `rerun_overlap` | 0.677 | | | | 5 |

## Breakdowns

| Breakdown | Runs flagged |
|---|---|
| `bd_scope_drift` | 0 of 5 |
| `bd_missed_key_paper` | 5 of 5 |
| `bd_opaque_screening` | 4 of 5 |
| `bd_cant_steer` | n/a |
| `bd_misattribution` | 2 of 5 |
| `bd_status_ignored` | 0 of 5 |

## Per run

| Run | `recall_gold` | `precision_set` | `off_scope_rate` | `claim_support_rate` | `trap_flag_rate` | `near_miss_exclusion_rate` | `exclusion_explained` | `steer_preservation` | `bd_scope_drift` | `bd_missed_key_paper` | `bd_opaque_screening` | `bd_cant_steer` | `bd_misattribution` | `bd_status_ignored` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261116T223651Z_1 | 0.588 | 0.974 | 0 | 0.8 | 1 | n/a | 0 | n/a | 0 | 1 | 1 | n/a | 0 | 0 |
| 20261116T223653Z_2 | 0.706 | 0.976 | 0 | 0.933 | 1 | n/a | 0 | n/a | 0 | 1 | 1 | n/a | 0 | 0 |
| 20261116T223655Z_3 | 0.588 | 0.954 | 0 | 1 | 1 | n/a | 0 | n/a | 0 | 1 | 1 | n/a | 1 | 0 |
| 20261116T223657Z_4 | 0.647 | 0.951 | 0 | 0.933 | 1 | n/a | 0 | n/a | 0 | 1 | 1 | n/a | 0 | 0 |
| 20261116T223659Z_5 | 0.647 | 0.949 | 0 | 0.933 | 1 | n/a | 1 | n/a | 0 | 1 | 0 | n/a | 1 | 0 |
