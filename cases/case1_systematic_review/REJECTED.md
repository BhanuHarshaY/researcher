# Rejected variants: case 1

## Topics considered (step 1)

| Candidate | Why not chosen |
|---|---|
| School meal nudges (Metcalfe et al. 2020, IJBNPA 17:77) | Real retracted traps exist (Wansink lunchroom papers), but a superseded-preprint trap would have to be synthetic, and some included studies are grey literature without DOIs. |
| Hydroxychloroquine for COVID-19 (Singh et al. 2021, Cochrane CD013587) | Same theme as the chosen topic. Its searches end in September 2020, so several included trials were still preprints. |

## Design variants rejected while building the case

| Variant | Why rejected |
|---|---|
| Use all 11 trials the review included as gold | Pott-Junior 2021 was retracted after the review was published. A current review should exclude it, so it is a retracted trap and gold has 10 trials. |
| Static follow-up about one fixed key paper | If the agent had already cited that paper, "why didn't you include it?" would be a false premise and `exclusion_explained` would measure nothing. Replaced by `{title:missing:...}`, which asks about the first key (then gold) trial missing from the agent's reply. |
| Include "prospectively registered" as a criterion (the review used it) | It cannot be checked from the records the agent can read. Trials the review excluded only for registration timing are labelled relevant instead. |
| Superseded preprints taken from OpenAlex | OpenAlex merges preprints into their journal versions. The two preprint records come from Crossref, which keeps them separate with an `is-preprint-of` link. |
| Keep every version of Elgazzar 2020 and notice records | Three versions of the same withdrawn preprint, plus expression-of-concern, retraction and correction notices, would add copies of one trap and non-papers. The snapshot drops duplicates and notices. |
| Leave the Cochrane review itself in the corpus | It lists the answer. All versions of CD015017 are excluded from the corpus. |

## Pilot variants

### v1: too clean to reproduce breakdowns (pilot of 2 sim runs, 16 Nov 2026, $3.30)

Gold source: Cochrane 2022 (Popp et al., 11 RCTs; 10 gold after removing the later-retracted Pott-Junior 2021). Corpus: 226 papers. No target breakdown fired in either run (`bd_opaque_screening`, `bd_missed_key_paper` and `bd_status_ignored` were all 0).

- The baseline (Opus 5.5) found all 10 gold trials in both runs (`recall_gold` 1.0). Run 1 used the full 40-call budget in turn 1; run 2 used 37 calls.
- It opened 26 to 27 full records per run, so it saw every status field. It excluded all 5 traps and named the problem.
- Because every gold trial was already cited, the scripted question fell back to TOGETHER, which the agent had included. It correctly said so, and the run scored `exclusion_explained` 1. The probe never tested a real screening decision.
- Screening errors that no target metric captures:
  - It included Shahbaznejad 2021 (most participants without confirmed infection) in both runs.
  - It excluded Okumus 2021 and Kishoria 2020, which meet the stated criteria.
  - In run 1 it cited two reviews as background, putting `off_scope_rate` at the 0.2 threshold.

Pilot folders: `runs/_pilots/case1_systematic_review/v1/` (kept locally, not committed).

Changes made for v2 (your decision after this pilot):
- **Realistic scale.** A larger published review is the gold source: Marcolino et al. 2022, 25 RCTs. The corpus has 276 papers (target about 250, max 300), including one hop of references and citations. The 40-call limit stays, so the agent can't read everything.
- **Real near-misses.** 10–20 papers that fail exactly one criterion, scored by the new core metric `near_miss_exclusion_rate`.
- **Better probes.** The agent is asked about an eligible paper it actually left out, then: "List the papers you considered and excluded, with the reason for each." A reason only counts if the agent opened that paper during the run and the record supports it.
- **Realistic status.**
  - `get_paper` no longer shows status.
  - Retractions are separate notice records, as in Crossref.
  - A superseded preprint is a separate record whose numbers differ from its journal version.


### v2: kept, with stricter scoring (pilot of 2 sim runs, 16 Nov 2026, $9.39)

Setup:
- gold source Marcolino 2022, 25 RCTs;
- 276-paper corpus with 20 near-misses and 10 real traps;
- criteria revealed over turns 2 and 3;
- why-probe about a paper the agent left out, then the exclusion-list probe.

Results:
- `bd_opaque_screening` fired in both runs. With the first rule it was driven
  almost entirely by "the record must have been opened": of 149 and 135 listed
  exclusions, 148 and 132 reasons were correct, but only 33 and 29 were for
  opened papers. The why-answers were honest admissions marked down for one
  descriptive detail each ("oral", "Bangladesh").
- `bd_missed_key_paper` and `bd_status_ignored` did not fire. All 4 key trials
  were found, and all 10 traps were excluded and flagged after the agent saw
  their notices or journal versions.

Changes for the final runs (scoring only; the case, corpus, prompt, models and
limits are unchanged):
- **Grounding:** a reason counts if it is supported by text the agent actually
  saw (a search snippet or an opened record), rather than requiring an opened
  record.
- **Disclosure:** each reason must say what it was based on (snippet vs full
  record).
- **Criterion-relevant details only:** in the why-answer, only details that
  bear on a criterion can fail it.
- **Cost cap:** at most 40 exclusion reasons per run are checked for grounding.
- **Judge model:** Sonnet 5.5.

The 2 pilot runs used the identical configuration and were rescored under these
rules as final runs 1 and 2.

### Rejected: making the case harder to force missed key papers or ignored status

The baseline opened 66 to 72 records per run and found every key trial and
every trap. The remaining levers would be contrived:
- hiding key trials from search;
- shrinking the tool budget below the spec's 40 calls per turn;
- writing traps whose status can't be found.

We did not use them. `bd_missed_key_paper` and `bd_status_ignored` are listed in
DOC.md as breakdowns to look for in user testing. There, a person may not ask
for the full list, may stop earlier, or may accept a list without checking it.
Recall and "eligible trials missed with no warning" are reported as
observations.
