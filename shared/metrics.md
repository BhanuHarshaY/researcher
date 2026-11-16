# Core metrics (shared across all cases)

Every run writes `reward.json` with the same fixed keys for every case and both
agents. A metric is `null` when it doesn't apply to the case or its denominator
is zero. Code: [harness/metrics/core.py](../harness/metrics/core.py) (pure
calculations), [judge.py](../harness/metrics/judge.py) (LLM judgments) and
[score.py](../harness/metrics/score.py) (which combines the two).

## How the inputs are produced

**Cited papers.** "Cited papers" means the papers that are part of the agent's
final answer. Checking which paper ids appear in the text is not enough: agents
also mention papers they exclude ("T009 is a K-12 study, excluded"), and they
update their answer across turns. So the judge model reads the whole
conversation and gives every paper id the agent mentioned one role as of the
end of the conversation:

- **included**: the paper is listed as included, or cited as evidence or
  background in the report.
- **excluded**: the agent explicitly excluded or removed it. This wins over
  other mentions.
- **mentioned**: the paper only came up in passing.

The judge also records whether the agent told the user about the paper's status
problem (retracted, or a preprint with a published version). Only ids that
really occur in the agent's messages are labelled; any other id the judge
returns is dropped.

**Claims checked.** A deterministic step picks candidate statements from all
agent messages:

- **What counts:** table rows and sentences that name at least one corpus id
  and have at least 6 other words. Duplicates are dropped.
- **Order:** candidates are shuffled with a fixed seed, so the same transcript
  always gives the same order.
- **How many:** up to 40 candidates go to the judge. Some will be statements
  the judge marks as not a claim, such as remarks about the agent's own
  searching. The first 15 checkable claims, in the shuffled order, are counted.

The judge sees each statement with the cited paper's record (metadata,
abstract, passages). It also sees the 3 most similar other papers (BM25),
which lets it spot a claim credited to the wrong paper.

The judge's context is capped at 40 papers per run and 6,000 characters of
passages per paper. Abstract-length passages never reach that cap.

**Why-question.** For the scripted "Why didn't you include X?" follow-up, the
harness first works out facts from the run log and corpus:

- whether X can be found by keyword search, or only through citation links
- whether X appeared in any tool result before the question
- whether the agent opened X with `get_paper`

The judge then decides whether the agent's answer is supported by X's record
and by those facts.

The judge model is `judge_model` in `config/models.yaml`, and it returns
schema-checked JSON. All judge labels are saved in `judgments.json` in the run
folder, so every number can be audited. Judge tokens are not counted in the
run's cost metrics.

## Metrics in `reward.json`

### Quality metrics

| Name | Definition | Computed as | `null` when |
|---|---|---|---|
| `recall_gold` | Gold papers cited in the final report ÷ findable gold papers | \|included ∩ gold in corpus\| ÷ \|gold in corpus\| | no gold paper is in the corpus |
| `precision_set` | Cited papers that are in `relevant_ids` ÷ all cited papers | \|included ∩ relevant_ids\| ÷ \|included\| | nothing cited |
| `off_scope_rate` | Cited papers in `off_scope_ids` ÷ all cited papers | \|included ∩ off_scope_ids\| ÷ \|included\| | nothing cited |
| `claim_support_rate` | Claims judged supported by the cited paper's passages ÷ claims checked (max 15 per run) | supported ÷ (supported + unsupported + misattributed), over the first 15 checkable claims. Statements the judge marks as not a claim are left out. | no statement was checkable |
| `trap_flag_rate` | Seeded traps flagged correctly in the report or excluded ÷ traps that appear in the corpus | A trap counts as handled unless it is included without its status flag | the case has no traps in the corpus |
| `exclusion_explained` | 1 if, when asked why a gold paper was left out, the agent gives a reason supported by that paper's record; else 0 | 1 if the judge says the reason is accurate: the record shows the paper fails a criterion, the agent truthfully describes its own process (for example, the paper never came up in its searches), or the agent correctly says the paper was included. 0 if no reason is given, or if anything in the answer is false, including saying or suggesting the paper isn't in the database. | the case has no why-question, or the run ended before it |
| `steer_preservation` | After a scripted criteria change: kept-and-still-valid papers ÷ papers that should have been kept | Should keep = included just before the change ∩ `post_change_expected_ids`. Kept = those still included at the end. | no criteria change in the case, the run ended before it, or nothing should have been kept |

### Cost metrics

These measure the agent only; sim-user and judge calls are not included.

| Name | Definition |
|---|---|
| `user_turns` | User messages sent (max 6) |
| `tool_calls` | Tool calls executed by the agent (max 40 per turn) |
| `input_tokens` | Agent input tokens, including cache reads and cache writes |
| `output_tokens` | Agent output tokens, including thinking |
| `wall_time_s` | Seconds from the first user message to the end of the conversation (survey and scoring not included) |

### Breakdown flags

Each flag is 1 if the breakdown happened, 0 if not, and `null` if the metric it
depends on is `null`. The thresholds come from `thresholds` in each case's
`case.yaml` (defaults: `off_scope` 0.2, `steer_preservation` 0.7).

| Name | 1 when |
|---|---|
| `bd_scope_drift` | `off_scope_rate` > the case's `off_scope` threshold |
| `bd_missed_key_paper` | any `key_ids` paper is not included in the final answer |
| `bd_opaque_screening` | `exclusion_explained` == 0 |
| `bd_cant_steer` | `steer_preservation` < the case's `steer_preservation` threshold |
| `bd_misattribution` | any checked claim is judged as credited to the wrong paper |
| `bd_status_ignored` | a retracted trap or superseded preprint is included without a status flag |

## Summary metrics (`summary.json`, `summary.md`)

`python -m harness.metrics.summarize --case <case> [--agent baseline] [--mode sim] [--last 5]`
aggregates the runs in `runs/<case>/<agent>/<mode>/`:

- **Each metric:** mean, SD, min, max and n, counting only non-null values.
- **`rerun_overlap`:** the mean pairwise Jaccard similarity of the cited-paper
  sets across runs. 1 means every run cited the same papers. Two empty sets
  count as identical.
- **Each `bd_*`:** how many runs showed it, out of the runs where it applies.

## Rescoring

Rescoring reruns only the judge (which costs money); the agent is not rerun:

```
docker compose run --rm harness python -m harness.metrics.score runs/<case>/<agent>/<mode>/<run>
```

It rewrites `reward.json` and `judgments.json` and keeps the original cost
metrics.
