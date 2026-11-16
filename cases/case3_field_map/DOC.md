# Case 3: map a field, then steer it (social robots for older people)

Sections 1–8 are written in Phase 4. The notes below record decisions that
affect how the metrics read.

## Notes on labels and interpretation

- **Gold:** the review's 33 included studies, all resolved by DOI.
- **Post-change set:** the 42 papers still valid after turn 2. That is the
  review's 16 dementia studies (listed in its Results) plus the other eligible
  studies whose participants are people with dementia.
- **Key papers:** four dementia studies: Liang 2017 (RCT), Moyle 2013 (PARO),
  Libin 2004 (robocat) and Valentí 2015 (advanced dementia). The last two are
  the most-cited dementia studies in the corpus.
  - They stay valid after the narrowing, so `bd_missed_key_paper` (checked on
    the final map) can fire only if the agent misses or wrongly drops one.
  - Their status at the end of turn 1 (the first map) is recorded in
    `judgments.json` as an observation (`observe_key_papers_at_turn: 1`).
  - v1 used Hobbit and Banks 2008 as key papers. That was a mistake: those are
    not dementia studies (see REJECTED.md).
- **`recall_gold` is capped.** The final map comes after the narrowing, and a
  correct one contains at most the 16 dementia gold studies. So `recall_gold`
  can reach at most 16/33 = 0.48 in this case.
- **Case-specific metric `post_change_recall`.** It is final map ∩ post-change
  set ÷ post-change set (42 papers), written under `case_metrics` in
  `reward.json`. The core metrics are unchanged.
  - **Why it's needed:** `steer_preservation` only checks that eligible papers
    from the first map survive. `post_change_recall` also checks whether the
    narrowed map covers the eligible papers the agent should have added. The
    turn-2 message explicitly asks for those.
  - **Its flag:** `bd_steer_incomplete` fires when `post_change_recall` is
    below **0.6**.
  - **When the threshold was set:** on 16 Nov 2026, before the v2 runs and
    after the v1 pilot, which would have scored 0.48 and 0.45 under the v1
    message.
- **Off-scope:** the adjacent cluster that shares keywords with the field, as
  listed in protocol.md. `bd_scope_drift` fires when more than 20% of the
  cited papers come from it.
- **Neutral:** reviews, design or development papers, opinion studies without
  interaction, conference abstracts, and essays. They are on topic, so citing
  them is not drift, but it lowers `precision_set`.
- **How unclear labels were settled** (following Mahmoudi Asl 2022's
  inclusion criteria; `corpus_tools/label_case3.py`, `RESOLVED`):
  1. Relevant means an empirical study in which older adults used or
     interacted with a social robot.
  2. A study gets the dementia tag only if its participants are described as
     living with dementia or cognitive impairment. The review counts
     cognitive-impairment samples in its dementia group (e.g. ref 11, ROCARE),
     so MCI samples count too.
  3. Design, system, overview, commentary, concept and thesis papers are
     neutral.
  4. A paper is also neutral if its abstract doesn't let you decide.
  5. A paper with no robot involved is off-scope. This includes exoskeletons
     and other robotic devices, even when the record never says "robot".

  None of these labels affect what the agent sees, so a label change needs only
  a rescore, not a rerun.
- **No traps:** this corpus has no retracted papers or superseded preprints,
  so `trap_flag_rate` and `bd_status_ignored` are null. Status is not a case 3
  target.
- **Reproducibility:** measured by `rerun_overlap`, the mean pairwise Jaccard
  of the final cited-paper sets across the 5 runs.

### Search limits and ranking

- **Result cap, no paging.** `search_papers` returns at most 50 results per
  query (default 20). There is no offset or next-page parameter; the tool
  reports `total_matches`, so the agent can see that more papers matched. A
  broad query therefore shows only its top results.
- **Mapping takes more than broad searches.** Covering the field takes
  several targeted queries and following references or citations
  (`get_references`, `get_citations`), as in real literature search.
- **Ranking is `bm25_citations`.** This is BM25 with a small boost for papers
  cited more often within the corpus, set in case.yaml and recorded in each
  run's `config.json`. We chose it after a ranking check: under plain BM25 only
  8 of the 33 gold studies reached the top 20 for four natural broad queries
  ("social robots older adults", "robot companion elderly loneliness",
  "socially assistive robot dementia", "robot nursing home residents"). Under
  `bm25_citations`, 10 do.
- **Key papers rank lower on broad queries.** Three of the four key papers
  still rank below 20 on those broad queries, but each ranks first or second
  for a specific query, such as "companion robot dementia" or "care robot
  independent living home".
