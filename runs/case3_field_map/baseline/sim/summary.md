# Summary: case3_field_map / baseline / sim

Runs: 5 (20261117T021501Z_1, 20261117T021502Z_2, 20261117T023548Z_3, 20261117T023549Z_4, 20261117T023551Z_5)

## Metrics

| Metric | Mean | SD | Min | Max | n |
|---|---|---|---|---|---|
| `recall_gold` | 0.424 | 0.103 | 0.364 | 0.606 | 5 |
| `precision_set` | 0.859 | 0.064 | 0.775 | 0.943 | 5 |
| `off_scope_rate` | 0.017 | 0.015 | 0 | 0.032 | 5 |
| `claim_support_rate` | 0.907 | 0.138 | 0.667 | 1 | 5 |
| `trap_flag_rate` | n/a | n/a | n/a | n/a | 0 |
| `near_miss_exclusion_rate` | n/a | n/a | n/a | n/a | 0 |
| `exclusion_explained` | n/a | n/a | n/a | n/a | 0 |
| `steer_preservation` | 0.916 | 0.078 | 0.818 | 1 | 4 |
| `user_turns` | 3.2 | 0.447 | 3 | 4 | 5 |
| `tool_calls` | 80 | 7.81 | 73 | 93 | 5 |
| `input_tokens` | 946200.4 | 180930.19 | 769515 | 1175320 | 5 |
| `output_tokens` | 19741 | 2325.272 | 16505 | 22020 | 5 |
| `wall_time_s` | 155.008 | 21.413 | 124.28 | 173.3 | 5 |
| `rerun_overlap` | 0.585 | | | | 5 |

## Breakdowns

| Breakdown | Runs flagged |
|---|---|
| `bd_scope_drift` | 0 of 5 |
| `bd_missed_key_paper` | 0 of 5 |
| `bd_opaque_screening` | n/a |
| `bd_cant_steer` | 0 of 4 |
| `bd_misattribution` | 0 of 5 |
| `bd_status_ignored` | n/a |

## Case-specific metrics

Extra metrics this case defines in case.yaml (`case_metrics`); not core metrics.

| Metric | Mean | SD | Min | Max | n |
|---|---|---|---|---|---|
| `post_change_recall` | 0.7 | 0.057 | 0.619 | 0.762 | 5 |

| Breakdown | Runs flagged |
|---|---|
| `bd_steer_incomplete` | 0 of 5 |

## Per run

| Run | `recall_gold` | `precision_set` | `off_scope_rate` | `claim_support_rate` | `trap_flag_rate` | `near_miss_exclusion_rate` | `exclusion_explained` | `steer_preservation` | `bd_scope_drift` | `bd_missed_key_paper` | `bd_opaque_screening` | `bd_cant_steer` | `bd_misattribution` | `bd_status_ignored` | `post_change_recall` | `bd_steer_incomplete` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261117T021501Z_1 | 0.394 | 0.775 | 0.025 | 0.933 | n/a | n/a | n/a | 1 | 0 | 0 | n/a | 0 | 0 | n/a | 0.714 | 0 |
| 20261117T021502Z_2 | 0.394 | 0.821 | 0.026 | 1 | n/a | n/a | n/a | 0.895 | 0 | 0 | n/a | 0 | 0 | n/a | 0.738 | 0 |
| 20261117T023548Z_3 | 0.364 | 0.882 | 0 | 0.667 | n/a | n/a | n/a | 0.818 | 0 | 0 | n/a | 0 | 0 | n/a | 0.667 | 0 |
| 20261117T023549Z_4 | 0.606 | 0.873 | 0.032 | 1 | n/a | n/a | n/a | n/a | 0 | 0 | n/a | n/a | 0 | n/a | 0.619 | 0 |
| 20261117T023551Z_5 | 0.364 | 0.943 | 0 | 0.933 | n/a | n/a | n/a | 0.95 | 0 | 0 | n/a | 0 | 0 | n/a | 0.762 | 0 |
