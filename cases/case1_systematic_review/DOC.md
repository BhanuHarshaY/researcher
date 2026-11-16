# Case 1: systematic review with explicit criteria (ivermectin for COVID-19)

Sections 1–8 (setup, target breakdowns, environment, external systems, task
and protocol, baseline results, proposed agent, rejected variants) are written
in Phase 4. The notes below record decisions that affect how the metrics read.

## Notes on labels and interpretation

### Neutral labels

88 of the 276 corpus papers are labelled **neutral** in
`corpus/labels.json`. They fall into four groups:
- **Retraction notices.** The 6 notices are how status shows; they are not
  studies.
- **Protocols and design papers.** These describe trials but don't report
  their results.
- **Secondary reports judged too borderline to score:**
  - Chahla 2022, where it is unclear whether the design is individually or
    cluster randomized;
  - the COVID-OUT long-COVID follow-up preprint;
  - the ACTIV-6 600 µg/kg preprint, whose journal article (2023) is a date
    near-miss.
- **Papers not about ivermectin for COVID-19**, such as other repurposed drugs
  or ivermectin for scabies.

A neutral paper is neither relevant nor off-scope. Citing one lowers
`precision_set`, because it adds to the cited papers without being relevant. It
doesn't change `off_scope_rate`, `recall_gold` or any breakdown flag. Borderline
reports were made neutral so that a reasonable judgment call is neither
rewarded nor punished as scope drift.

### Trials, not reports

`recall_gold` and `bd_missed_key_paper` count trials. The case's `report_of`
map links each superseded preprint, and the ACTIV-6 conference abstract, to
the trial's main report. Citing any report of a gold trial therefore counts
that trial as found. Citing the superseded preprint instead of the journal
article is scored separately, by `trap_flag_rate` and `bd_status_ignored`.

### Citations outside the corpus

An id-like citation that isn't in the corpus (an OpenAlex-style id, or a DOI
or PMID in brackets) counts as a cited paper that is not relevant, and any
statement citing it is scored unsupported. Author–year citations without an
id are not detected.

### Possible training-data knowledge of well-known retractions

Some of this case's traps were widely reported before the agent model's
training cut-off:
- the withdrawal of Elgazzar 2020 (July 2021);
- the retraction of Samaha 2021;
- the published reviews themselves (Marcolino 2022, Cochrane 2022).

The agent may therefore exclude or flag a trap from memory rather than by
finding the retraction notice in the corpus.

What we do about it:
- **`trap_evidence` in each run's `judgments.json`** records whether the agent
  saw the trap's notice (or the preprint's journal version) in any tool result.
  `flagged_without_seen_evidence: true` marks a flag that did not come from
  the tools. Section 6 reports these counts next to `trap_flag_rate`.
- **Less-publicised retractions are a useful contrast.** IRICT 2022 (retracted
  2024), Pott-Junior 2021, and the microbiome hypothesis paper are less likely
  to be memorized, so compare their flag rates with Elgazzar's.
- **The baseline and the proposed agent use the same model,** so comparisons
  between them stay fair. Absolute trap scores may still overstate behaviour
  that is grounded in the tools.

## Notes on the final runs

### Runs 1 and 2 were pilots with identical configuration

Final runs 1 and 2 are the two v2 pilot runs (16 Nov 2026). They used exactly
the configuration of runs 3–5. We checked the hashes in each `config.json`
against the final files:
- corpus, labels, `case.yaml` and baseline prompt;
- agent and sim-user models;
- tool limits (40 calls per turn, 6 user turns);
- SDK version and git commit.

Prompt caching was on in all five runs; about 92% of the agent's input tokens
were cache reads. After the pilot, only the scoring changed (see
REJECTED.md, v2), so runs 1 and 2 were rescored with the final rules and the
final judge model (Sonnet 5.5). Runs 3–5 were run in parallel.

### Breakdowns not forced in sim mode

In the pilots the baseline found every key trial and handled every trap
correctly, after seeing the evidence in its tool results. We did not make the
case artificially harder to force `bd_missed_key_paper` or `bd_status_ignored`
(see REJECTED.md). Both stay in the case and are the breakdowns to watch for in
user testing. There, a person may not ask for the full list, may stop sooner,
or may accept a list without checking its sources.

### Observations reported alongside the metrics

These come from `observations` in each run's `judgments.json`. They are not
core metrics, and `bd_missed_key_paper` is unchanged.
- recall of gold trials, and which eligible trials (gold or other relevant)
  the final answer missed;
- whether eligible trials were missed **with no warning**, meaning the agent
  never told the researcher that its list might be incomplete.

The per-run values are in section 6.

