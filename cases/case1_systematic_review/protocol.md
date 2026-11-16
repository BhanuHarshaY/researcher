# Protocol: case 1 (systematic review with explicit criteria)

Both modes use the same chat channel, the same fixed first message, the same
agent, tools and frozen corpus, and the same metrics (shared/metrics.md).

## Task

The user runs a systematic review: do randomized trials show that ivermectin
works for treating COVID-19? Like a real researcher, the user starts with an
underspecified request and gives the inclusion criteria over the next two
turns. The gold set is the 25 trials included by Marcolino et al. (2022).

The frozen corpus (276 papers, corpus/SOURCES.md) is a realistic slice of this
literature, too large to read within the 40-tool-call limit. It holds:
- the gold trials, and other eligible trials;
- 18 near-misses that each fail exactly one criterion;
- 6 retracted or withdrawn reports, each with its real retraction notice as a
  separate record;
- 4 preprints superseded by journal versions with different numbers;
- reviews, lab studies and commentary.

No tool shows publication status, which matches how status appears in real
sources: the agent has to notice the notices and the duplicate versions. Every
paper's label and reason is in corpus/labels.json.

## Sim mode

```
docker compose run --rm harness python -m harness.run --case case1_systematic_review --mode sim --agent baseline --runs 5
```

1. Turn 1 sends the underspecified `initial_prompt` verbatim.
2. Turns 2 and 3 (scripted) give the criteria in two parts and ask for the full
   updated list of included trials.
3. Turn 4 (scripted) asks: "Why didn't you include "<title>"?" The title is the
   first eligible paper the agent's latest list left out, checking the key
   trials (TOGETHER, ACTIV-6, I-TECH, López-Medina) first, then other gold,
   then other eligible trials. The harness picks it; the sim user never sees
   the gold set.
4. Turn 5 (scripted) asks: "List the papers you considered and excluded, with
   the reason for each."
5. The persona (persona.md) then sends `/done`, after at most one clarifying
   question. The hard cap is 6 user turns.

## Human mode

```
docker compose run --rm harness python -m harness.run --case case1_systematic_review --mode human --agent baseline
```

Brief the participant with this text, read aloud or on paper, and give them the
criteria card below:

> You are a PhD student doing a systematic review for a methods course: do
> randomized trials show that ivermectin works for COVID-19? The opening
> request is sent for you and does not mention your criteria. Give the
> assistant your criteria from the card over your next one or two messages,
> as you would in real life. From your own reading you know of four major
> trials and expect them to be considered: TOGETHER (NEJM 2022), ACTIV-6 (JAMA
> 2022), I-TECH (JAMA Internal Medicine 2022) and the López-Medina trial (JAMA
> 2021). Work with the assistant until you have a review you would hand in and
> could defend. Ask about anything you expected to see, and ask the assistant
> to justify its exclusions. You have about 20 minutes.

Criteria card:
- randomized controlled trials only
- oral or intravenous ivermectin
- people with confirmed or suspected COVID-19 (treatment, not prophylaxis)
- compared with placebo, no treatment, standard care or another drug
- any other treatments the same in both arms
- published 2020 to 2022
- no retracted or withdrawn reports
- journal article over its preprint
- no lab or animal studies, no reviews

Session rules:
- The first message is sent automatically and printed. The participant then
  types; a message ends with an empty line.
- Typing `/done` ends the session (at most 6 user turns).
- The terminal then gives the survey (shared/survey_interview.md), saved as
  `survey.json`.
- The interviewer runs the 5–10 minute interview and writes notes in the run's
  `interview_notes.md`.
- Do not tell the participant about the traps, near-misses, gold set or
  metrics.
- The scripted probes are not scored in human mode (`exclusion_explained` is
  null). The interview covers screening transparency instead.

## Outputs

`runs/case1_systematic_review/baseline/<mode>/<timestamp>_<n>/` with
`trajectory.json`, `reward.json`, `config.json` and `judgments.json`. Human mode
adds `survey.json` and `interview_notes.md`.
