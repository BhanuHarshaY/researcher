# Survey and interview (shared across all cases)

Every human-mode run ends with this survey, which the harness gives in the
terminal right after the session. The answers are saved to `survey.json` in the
run folder. The interviewer then runs the short interview below and writes notes
in the run's `interview_notes.md` template.

## Survey

### Cognitive load: Raw NASA-TLX (0–100 each)

Physical demand is left out because it doesn't apply. Raw TLX is the plain mean
of the five subscales; no pairwise weighting is used.

| Subscale | Question | 0 means | 100 means |
|---|---|---|---|
| Mental demand | How mentally demanding was the task? | Very low | Very high |
| Temporal demand | How hurried or rushed was the pace of the task? | Very low | Very high |
| Performance | How successful were you in accomplishing what you were asked to do? | Perfect | Failure |
| Effort | How hard did you have to work to accomplish your level of performance? | Very low | Very high |
| Frustration | How insecure, discouraged, irritated, stressed, and annoyed were you? | Very low | Very high |

### Statements (1–7: 1 = strongly disagree, 4 = neutral, 7 = strongly agree)

Perceived controllability:
1. I could steer which papers the agent included.
2. I could change my criteria without losing the work already done.
3. I understood why papers were included or left out.
4. I could check where each claim in the report came from.

Trust and reliance:

5. I trust the paper set the agent produced.
6. I would cite this report's claims without checking them myself. *(Reverse-coded check against over-trust.)*
7. I would be comfortable defending this review to my advisor or a reviewer.

Engagement:

8. I stayed actively involved in the review rather than just reading the output.

### Scores saved in `survey.json`

| Score | How it's computed |
|---|---|
| `raw_tlx` | Mean of the five TLX subscales (0–100; higher means more load) |
| `controllability` | Mean of items 1–4 |
| `trust` | Mean of items 5 and 7 |
| `over_reliance` | Item 6 as answered (higher means more over-trust). It is also stored reverse-coded (8 − answer) as `item6_reversed`. |
| `engagement` | Item 8 |

Every raw answer is also saved. A skipped item is `null` and is left out of the
means.

## Interview (5–10 min)

1. Walk me through a moment where you felt least in control. What would you have wanted to do?
2. Was there a paper you expected to see? How did you find out whether it was included?
3. When you asked the agent to change course, did the result match what you meant?
4. How would you check this report before using it in your own paper?
5. What one change would make you trust this tool more?
