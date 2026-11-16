# Summary: case1_systematic_review / baseline / sim

Runs: 5 (20261116T211756Z_1, 20261116T212646Z_2, 20261116T214845Z_3, 20261116T214847Z_4, 20261116T214849Z_5)

## Metrics

| Metric | Mean | SD | Min | Max | n |
|---|---|---|---|---|---|
| `recall_gold` | 0.904 | 0.061 | 0.84 | 0.96 | 5 |
| `precision_set` | 0.928 | 0.016 | 0.906 | 0.943 | 5 |
| `off_scope_rate` | 0.042 | 0.016 | 0.029 | 0.062 | 5 |
| `claim_support_rate` | 0.893 | 0.036 | 0.867 | 0.933 | 5 |
| `trap_flag_rate` | 0.96 | 0.055 | 0.9 | 1 | 5 |
| `near_miss_exclusion_rate` | 0.95 | 0 | 0.95 | 0.95 | 5 |
| `exclusion_explained` | 0 | 0 | 0 | 0 | 5 |
| `steer_preservation` | n/a | n/a | n/a | n/a | 0 |
| `user_turns` | 5.2 | 0.447 | 5 | 6 | 5 |
| `tool_calls` | 81.8 | 5.975 | 73 | 88 | 5 |
| `input_tokens` | 3039749 | 181578.013 | 2768851 | 3241366 | 5 |
| `output_tokens` | 33295 | 3001.376 | 29388 | 36605 | 5 |
| `wall_time_s` | 326.812 | 24.339 | 292.55 | 352.05 | 5 |
| `rerun_overlap` | 0.86 | | | | 5 |

## Breakdowns

| Breakdown | Runs flagged |
|---|---|
| `bd_scope_drift` | 0 of 5 |
| `bd_missed_key_paper` | 0 of 5 |
| `bd_opaque_screening` | 5 of 5 |
| `bd_cant_steer` | n/a |
| `bd_misattribution` | 0 of 5 |
| `bd_status_ignored` | 2 of 5 |

## Per run

| Run | `recall_gold` | `precision_set` | `off_scope_rate` | `claim_support_rate` | `trap_flag_rate` | `near_miss_exclusion_rate` | `exclusion_explained` | `steer_preservation` | `bd_scope_drift` | `bd_missed_key_paper` | `bd_opaque_screening` | `bd_cant_steer` | `bd_misattribution` | `bd_status_ignored` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261116T211756Z_1 | 0.96 | 0.943 | 0.029 | 0.867 | 1 | 0.95 | 0 | n/a | 0 | 0 | 1 | n/a | 0 | 0 |
| 20261116T212646Z_2 | 0.92 | 0.939 | 0.03 | 0.867 | 1 | 0.95 | 0 | n/a | 0 | 0 | 1 | n/a | 0 | 0 |
| 20261116T214845Z_3 | 0.84 | 0.935 | 0.032 | 0.867 | 1 | 0.95 | 0 | n/a | 0 | 0 | 1 | n/a | 0 | 0 |
| 20261116T214847Z_4 | 0.96 | 0.914 | 0.057 | 0.933 | 0.9 | 0.95 | 0 | n/a | 0 | 0 | 1 | n/a | 0 | 1 |
| 20261116T214849Z_5 | 0.84 | 0.906 | 0.062 | 0.933 | 0.9 | 0.95 | 0 | n/a | 0 | 0 | 1 | n/a | 0 | 1 |
