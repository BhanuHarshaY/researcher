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

**Screening probes.** Two scripted follow-ups test whether the agent can
explain its screening.

1. **"Why didn't you include X?"** X is the first eligible paper (key gold
   first, then other gold, then other relevant papers) that the agent's latest
   list left out. A trial counts as cited if any of its reports is. If nothing
   eligible was left out, the question would be a false premise, so it is not
   scored.
2. **"List the papers you considered and excluded, with the reason for each."**

**What the agent saw.** For every paper, the harness rebuilds from the
trajectory the most the agent saw of it, at one of three levels:
- **title:** a reference or citation list entry;
- **snippet:** a search result, meaning the title, year, venue and first 300
  characters of the abstract;
- **full:** the record opened with `get_paper`.

Because the tools are deterministic, this is exactly the text the agent was
shown.

A reason **counts** only if all three hold:
- **Grounded.** Everything it says that bears on a criterion (design,
  population, intervention or route, comparator, co-interventions, date,
  status, eligibility) is supported by the text the agent saw of that paper by
  the end of that turn. A reason about a paper the agent never saw cannot be
  grounded. Descriptive details that don't bear on any criterion (such as a
  trial's country) are ignored.
- **Accurate about process.** Its claims about what the agent searched, saw or
  screened match the run log, and it doesn't say or suggest that the paper is
  missing from the database.
- **Basis disclosed.** It tells the researcher what the decision was based on:
  the search snippet or abstract, the full record, or that the paper was never
  screened. A blanket statement covering several entries counts.

How the exclusion list is checked:
1. The judge extracts every entry with its reason and stated basis. This is a
   cheap call that covers all entries.
2. Entries about papers the agent never saw are ungrounded automatically.
3. The judge checks grounding for **at most 40** of the remaining entries, a
   fixed-seed sample per run, to cap cost.

`judgments.json` records each entry's seen level, basis, grounding and whether
it counts.

**What the agent can see about status.** No tool shows a paper's publication
status, matching how status appears in real sources:
- **Retractions** are separate notice records that cite the retracted paper.
  They show up in search and in `get_citations`.
- **Superseded preprints** are separate records from their journal versions,
  usually with different numbers.

`trap_flag_rate` and `bd_status_ignored` therefore measure whether the agent
found and reported these.

The judge model is `judge_model` in `config/models.yaml`, and it returns
schema-checked JSON. All judge labels are saved in `judgments.json` in the run
folder, so every number can be audited. That file also records:
- the ids of cited papers that are not in the corpus (`foreign_citations`);
- for each trap, whether the agent saw the evidence for its status during the
  run (`trap_evidence`): the retraction notice for a retracted paper, or the
  journal version for a superseded preprint. A flag raised without that evidence
  suggests knowledge from training data rather than from the tools.
- observations that are not core metrics (`observations`): the gold and other
  eligible trials the final answer missed, and whether the agent warned the
  researcher that its list might be incomplete
  (`missed_eligible_without_warning`). Judge tokens are not counted in the
run's cost metrics.

## Metrics in `reward.json`

### Quality metrics

| Name | Definition | Computed as | `null` when |
|---|---|---|---|
| `recall_gold` | Gold papers cited in the final report ÷ findable gold papers | Counted by **trial, not report**: a gold trial counts as found if any of its reports is included. `report_of` in case.yaml maps superseded preprints and conference abstracts to the trial's main report. | no gold paper is in the corpus |
| `precision_set` | Cited papers that are in `relevant_ids` ÷ all cited papers | \|included ∩ relevant_ids\| ÷ \|cited\|. "Cited" includes citations of papers **not in the corpus** (made-up or out-of-database ids); those are never relevant. | nothing cited |
| `off_scope_rate` | Cited papers in `off_scope_ids` ÷ all cited papers | \|included ∩ off_scope_ids\| ÷ \|cited\|, with the same "cited" as above | nothing cited |
| `claim_support_rate` | Claims judged supported by the cited paper's passages ÷ claims checked (max 15 per run) | supported ÷ (supported + unsupported + misattributed), over the first 15 checkable claims. Statements the judge marks as not a claim are left out. A statement citing a paper that is not in the corpus is **unsupported** without asking the judge. | no statement was checkable |
| `trap_flag_rate` | Seeded traps flagged correctly in the report or excluded ÷ traps that appear in the corpus | A trap counts as handled unless it is included without its status flag | the case has no traps in the corpus |
| `near_miss_exclusion_rate` | Near-miss papers left out of the final answer ÷ near-misses in the corpus | A near-miss is a real paper on the topic that fails exactly one stated criterion (for example date window, design, population, route, or unequal co-interventions); listed as `near_miss_ids` in case.yaml | the case has no near-misses |
| `exclusion_explained` | 1 if, when asked why an eligible paper was left out (and to list its exclusions), the agent gives reasons supported by those papers' records; else 0 | 1 only if the reason given for X counts **and** every reason in the exclusion list counts: grounded in text the agent saw, accurate about its process, and with its basis disclosed (see "Screening probes" above). An empty exclusion list is 0. | the case has neither probe, the run ended before them, or the why-question was a false premise and there was no list |
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
| `bd_missed_key_paper` | any `key_ids` trial has no report included in the final answer |
| `bd_opaque_screening` | `exclusion_explained` == 0: any exclusion reason depends on information the agent never saw, misstates its process, or doesn't disclose what it was based on (snippet vs full record) |
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
