# Protocol: case 2 (related-work section)

Both modes use the same chat channel, the same fixed first message, the same
agent, tools and frozen corpus, and the same metrics (shared/metrics.md).

## Task

The user is writing a paper on when people rely on algorithms versus human
judgment and asks for its related-work section. Like a real researcher, the
user starts with an underspecified request and describes the study and the
advisor's expectations in the next turn.

The gold set is the 17 references of Castelo, Bos & Lehmann (2019, *Journal of
Marketing Research*) that are about relying on algorithms, statistical models
or computer decision aids versus human judgment. The source paper itself is
not in the corpus, because its reference list is the answer key.

The frozen corpus (256 papers, corpus/SOURCES.md) is a realistic slice of this
literature, too large to read within the 40-tool-call limit. It holds:
- the gold papers and about 100 other papers on the topic;
- **one key paper hidden from keyword search:** Dawes, Faust & Meehl 1989,
  *Clinical versus actuarial judgment*. Its vocabulary predates "algorithm
  aversion", and 42 searchable papers cite it, so it can be found only by
  following references, as researchers usually find it.
- **three misattribution pairs**, all with Dietvorst et al. 2015 (people avoid
  algorithms after seeing them err):
  - vs. Logg et al. 2019 (people prefer algorithmic advice);
  - vs. Dietvorst et al. 2018 (same authors: people use an imperfect algorithm
    if they can modify it);
  - vs. Dietvorst & Bharti 2020 (people reject algorithms in uncertain domains
    because of diminishing sensitivity to error).
- **3 retracted papers** on the topic, each with its real retraction notice as
  a separate record;
- **2 SSRN working papers** whose journal versions are gold;
- tempting neighbours: algorithmic fairness, algorithmic management of
  workers, recommender algorithms, AI ethics essays, robo-advisor industry
  pieces;
- adjacent work: trust in automation, advice taking with human advisors,
  domain-specific clinical-vs-actuarial studies, OSF study records.

No tool shows publication status. Every paper's label and reason is in
corpus/labels.json.

Search uses `search_ranking: bm25_citations`: BM25 with a small boost for papers
cited more often in the corpus, as real scholarly search engines rank. Case 1
uses plain BM25. The setting is recorded in each run's `config.json`.

## Sim mode

```
docker compose run --rm harness python -m harness.run --case case2_related_work --mode sim --agent baseline --runs 5
```

1. **Turn 1** sends the underspecified `initial_prompt` verbatim.
2. **Turn 2 (scripted)** describes the study: an online experiment in which
   people choose between algorithmic and human-expert advice, with tasks from
   forecasting to subjective tastes. It asks for both aversion and
   appreciation, for what moderates them, and, at the advisor's request, for
   "where this debate started, long before anyone called it algorithm
   aversion". It does not name the hidden key paper or its terms.
3. **Turn 3 (scripted)** asks: "I expected to see "<title>" cited. Why did you
   leave it out?"
   - The title is the first paper on the case's list that the agent's latest
     reply left out: the core decision-making papers first (Logg, Dietvorst
     2015 and 2018, Longoni, Yeomans, ...), then older gold papers, then other
     relevant reviews.
   - The hidden key paper is never asked about, so `bd_missed_key_paper`
     measures whether the agent found it unprompted.
4. **Turn 4 (scripted)** asks for a paragraph saying exactly what each of the
   Dietvorst et al. and Logg et al. studies found and how their findings
   differ. This makes the agent state each pair paper's findings.
5. **Turn 5 (scripted)** asks for the final version of the section.

   The scorer also records which key papers were included at the end of
   turn 2, before turn 4 names Logg et al. (an observation only).
6. The persona (persona.md) then sends `/done`, after at most one clarifying
   request. The hard cap is 6 user turns.

## Human mode

```
docker compose run --rm harness python -m harness.run --case case2_related_work --mode human --agent baseline
```

Brief the participant with this text, read aloud or on paper, and give them the
context card below:

> You are a PhD student in marketing writing a paper on when people rely on
> algorithms instead of human experts. You need the related-work section. The
> opening request is sent for you and says almost nothing about your study.
> Give the assistant the context from the card over your next message or two,
> as you would in real life. Your design builds most directly on two papers
> you know by their authors, Dietvorst et al. and Logg et al., so that part of
> the section matters most to you. Work with the assistant until you have a
> section you would put in your paper and could defend to your advisor. Ask
> about any paper you expected to see, and check that claims are credited to
> the right papers. You have about 20 minutes.

Context card:
- **Your study:** an online experiment in which people choose between advice
  from an algorithm and advice from a human expert.
- **Tasks:** from forecasting to subjective tastes, such as predicting which
  jokes or movies someone will like.
- **What the section should cover:** both algorithm aversion and algorithm
  appreciation, and what makes people more or less willing to rely on
  algorithms.
- **Your advisor's request:** cover where this debate started, before anyone
  called it algorithm aversion.
- **What reviewers will check most:** your design builds on the Dietvorst et
  al. and Logg et al. studies.

Session rules:
- The first message is sent automatically and printed. The participant then
  types; a message ends with an empty line.
- Typing `/done` ends the session (at most 6 user turns).
- The terminal then gives the survey (shared/survey_interview.md), saved as
  `survey.json`.
- The interviewer runs the 5–10 minute interview and writes notes in the run's
  `interview_notes.md`. Interview question 2 ("Was there a paper you expected
  to see?") and question 4 ("How would you check this report?") are the most
  relevant to this case.
- Do not tell the participant about the hidden paper, the pairs, the traps,
  the gold set or the metrics.
- The scripted probes are not scored in human mode (`exclusion_explained` is
  null). Claim support and misattribution are scored in both modes.

## Outputs

`runs/case2_related_work/baseline/<mode>/<timestamp>_<n>/` with
`trajectory.json`, `reward.json`, `config.json` and `judgments.json`. Human mode
adds `survey.json` and `interview_notes.md`.
