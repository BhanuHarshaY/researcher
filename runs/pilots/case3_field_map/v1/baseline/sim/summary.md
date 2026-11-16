# Summary: case3_field_map / baseline / sim

Runs: 2 (20261116T223155Z_1, 20261116T223156Z_2)

## Metrics

| Metric | Mean | SD | Min | Max | n |
|---|---|---|---|---|---|
| `recall_gold` | 0.273 | 0.043 | 0.242 | 0.303 | 2 |
| `precision_set` | 0.75 | 0.027 | 0.731 | 0.769 | 2 |
| `off_scope_rate` | 0.038 | 0 | 0.038 | 0.038 | 2 |
| `claim_support_rate` | 0.933 | 0.094 | 0.867 | 1 | 2 |
| `trap_flag_rate` | n/a | n/a | n/a | n/a | 0 |
| `near_miss_exclusion_rate` | n/a | n/a | n/a | n/a | 0 |
| `exclusion_explained` | n/a | n/a | n/a | n/a | 0 |
| `steer_preservation` | 0.932 | 0.096 | 0.864 | 1 | 2 |
| `user_turns` | 3 | 0 | 3 | 3 | 2 |
| `tool_calls` | 40 | 0 | 40 | 40 | 2 |
| `input_tokens` | 737174.5 | 58597.232 | 695740 | 778609 | 2 |
| `output_tokens` | 16626.5 | 475.883 | 16290 | 16963 | 2 |
| `wall_time_s` | 169.65 | 4.907 | 166.18 | 173.12 | 2 |
| `rerun_overlap` | 0.677 | | | | 2 |

## Breakdowns

| Breakdown | Runs flagged |
|---|---|
| `bd_scope_drift` | 0 of 2 |
| `bd_missed_key_paper` | 2 of 2 |
| `bd_opaque_screening` | n/a |
| `bd_cant_steer` | 0 of 2 |
| `bd_misattribution` | 0 of 2 |
| `bd_status_ignored` | n/a |

## Per run

| Run | `recall_gold` | `precision_set` | `off_scope_rate` | `claim_support_rate` | `trap_flag_rate` | `near_miss_exclusion_rate` | `exclusion_explained` | `steer_preservation` | `bd_scope_drift` | `bd_missed_key_paper` | `bd_opaque_screening` | `bd_cant_steer` | `bd_misattribution` | `bd_status_ignored` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261116T223155Z_1 | 0.303 | 0.769 | 0.038 | 1 | n/a | n/a | n/a | 1 | 0 | 1 | n/a | 0 | 0 | n/a |
| 20261116T223156Z_2 | 0.242 | 0.731 | 0.038 | 0.867 | n/a | n/a | n/a | 0.864 | 0 | 1 | n/a | 0 | 0 | n/a |
