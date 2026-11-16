# Protocol: case 3 (map a field, then steer it)

Both modes use the same chat channel, the same fixed first message, the same
agent, tools and frozen corpus, and the same metrics (shared/metrics.md).

## Task

The user asks the agent to map research on social robots used with older
people, then narrows the map to people living with dementia and asks for any
relevant studies it missed. The gold set is
the 33 studies included by Mahmoudi Asl et al. (2022, JMIR). The post-change
set (42 papers) is that review's 16 dementia studies, plus other eligible
studies in the corpus with people living with dementia or cognitive impairment.

The frozen corpus (286 papers, corpus/SOURCES.md) contains:
- the field itself;
- an **adjacent cluster that shares keywords**: rehabilitation, assistive and
  surgical robots, exoskeletons, telepresence-only robots, social robots for
  children with autism, and smart homes without robots;
- reviews, design papers and opinion studies, which are labelled neutral.

Every paper's label and reason is in corpus/labels.json.

## Sim mode

```
docker compose run --rm harness python -m harness.run --case case3_field_map --mode sim --agent baseline --runs 5
```

1. **Turn 1** sends `initial_prompt` verbatim: a broad request for a map of
   studies where a social robot was actually used with older people.
2. **Turn 2** (scripted criteria change): "Keep only studies with people
   living with dementia, and add any relevant ones you missed."
   `steer_preservation` compares the map just before this turn with the final
   map. The case-specific `post_change_recall` measures how many of the 42
   eligible papers the final map contains.
3. **Turn 3** (scripted): "Which papers from your first map did you drop, and
   why?"
4. The persona then sends `/done`, after at most one clarifying question. The
   hard cap is 6 user turns.

## Human mode

```
docker compose run --rm harness python -m harness.run --case case3_field_map --mode human --agent baseline
```

Brief the participant with this text, read aloud or on paper:

> You are a postdoc starting a project on social robots for older people. The
> opening request is sent for you. After the assistant's first map, narrow it:
> you only want studies where the robot was used with people living with
> dementia, you want any relevant ones it missed added, and you don't want to
> lose the work that still fits. Check what
> was dropped and why. Work with the assistant until you have a map you would
> use to plan your study. You have about 20 minutes.

- The first message is sent automatically. The participant types the rest; a
  message ends with an empty line.
- `/done` ends the session (at most 6 user turns).
- Then come the survey (shared/survey_interview.md, saved as `survey.json`) and
  a 5–10 minute interview (notes in the run's `interview_notes.md`).
- Do not tell the participant about the gold set, the adjacent cluster or the
  metrics.
- In human mode `steer_preservation` and `post_change_recall` are computed
  only if the person's narrowing message arrives at turn 2, as in the script. Otherwise it is null,
  and the interview covers steering instead.

## Outputs

`runs/case3_field_map/baseline/<mode>/<timestamp>_<n>/` with `trajectory.json`,
`reward.json`, `config.json` and `judgments.json`. Human mode adds
`survey.json` and `interview_notes.md`. `summarize.py` adds `rerun_overlap`
across the 5 runs.
