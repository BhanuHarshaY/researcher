# Case 2: related-work section (relying on algorithms vs. human judgment)

Sections 1–8 (setup, target breakdowns, environment, external systems, task
and protocol, baseline results, proposed agent, rejected variants) are written
in Phase 4. The notes below record decisions that affect how the metrics read.

## How the corpus is built

```
python3 -m corpus_tools.snapshot cases/case2_related_work/corpus/snapshot.json
python3 cases/case2_related_work/build/label.py
python3 cases/case2_related_work/build/write_yaml.py
docker compose run --rm harness python -m corpus_tools.validate case2_related_work
```

The snapshot spec (`corpus/snapshot.json`) does two things beyond case 1's:
- `abstract_fallback: "semanticscholar"` fills missing abstracts of curated
  papers. The response is frozen in `corpus/s2_abstracts.json`, so rebuilding
  needs no new request.
- `hidden_from_search` hides the key paper from search.

Rebuilding with these settings reproduces `papers.jsonl` byte for byte.

## Search ranking

`search_ranking: bm25_citations` (case.yaml, recorded in `config.json`)
multiplies the BM25 score by 1 + 0.1 · ln(1 + citations in the corpus). Case 1
uses plain BM25.

Without the boost, the query "algorithm aversion" ranked Dietvorst et al. 2015
40th. About 80 corpus papers repeat the phrase in their titles, and plain BM25
favours them over the paper that coined it. With the boost it ranks 5th:

| Query | Paper | Plain BM25 rank | With citation boost |
|---|---|---|---|
| algorithm aversion | Dietvorst 2015 | 40 | **5** |
| algorithm aversion | Dietvorst 2018 | 25 | **3** |
| algorithm appreciation | Logg 2019 | 7 | **1** |
| clinical versus statistical prediction | Grove 2000 | 4 | **1** |

For "algorithm aversion", the papers ranked 1st and 2nd are the Jussupow 2020
and Burton 2020 reviews. Dawes et al. 1989 stays hidden from search.

Grove 2000 now ranks first for "clinical versus statistical prediction", and it
cites the hidden key paper. So the origin path through references is somewhat
easier to find than before, as it is with real search engines.

## Notes on labels and interpretation

### Where the pair papers' text comes from

- **Logg, Minson & Moore 2019 (journal version):** OpenAlex has no abstract
  for it (Elsevier). Its passages come from the journal abstract in Semantic
  Scholar. That abstract was available, so the **primary misattribution pair
  is Dietvorst et al. 2015 vs. Logg et al. 2019**, and Dietvorst 2015 vs.
  Dietvorst 2018 is the secondary pair. The fallback, scoring Logg only against
  its SSRN text, was not needed.
- **The two SSRN working papers (Logg 2017, Dietvorst 2015):** their text
  comes from Crossref. They are separate records, mapped to their journal
  versions by `report_of`.

### Title-only records

Four curated papers have no abstract in OpenAlex, PubMed or Semantic Scholar.
The agent sees only their metadata:
- Sniezek & Buckley 1995 (gold);
- Dzindolet et al. 2003;
- Li, Hess & Valacich 2008;
- Kawaguchi 2021 (Semantic Scholar had only a truncated snippet).

A claim citing one of them can be checked only against the title. A judge
label of "unsupported" there may reflect missing text rather than an agent
error, so read `judgments.json` before counting it.

### The hidden key paper

Dawes, Faust & Meehl 1989 (W2012218966) is `hidden_from_search`. It is in the
`references` of 42 searchable papers, including Dietvorst 2015, Dietvorst 2018,
Dietvorst & Bharti 2020, Logg 2019 and Grove et al. 2000.

`observe_key_papers_at_turn: 2` records, in `judgments.json`
(`observations.key_papers_at_turn`), whether each key paper was included at
the end of turn 2. That is after the origins hint and before turn 4 names
Logg et al. In the v1 pilot the agent found Dawes 1989 only in turn 4, through
`get_references(Logg 2019)`, after telling the user in turn 1 that the classic
sources were not in the database. The final-report metric
`bd_missed_key_paper` can't see that. The observation is not a metric and
does not change `bd_missed_key_paper`.

No scripted message names it. The turn-2 request to cover "where this debate
started, long before anyone called it algorithm aversion" is the only hint.

`key_ids` also contains Dietvorst 2015 and Logg 2019, so `bd_missed_key_paper`
fires when any of the three is missing. `judgments.json` (`included_ids`) shows
which one.

An agent may write about Dawes et al. or Meehl from memory without a corpus id.
Author–year mentions without an id are not detected as citations, so the paper
still counts as missed. That is intended: the case tests finding the paper in
the database.

### Misattribution and claim sampling

The case has three pairs, all with Dietvorst et al. 2015: vs. Logg et al.
2019 (opposite findings), vs. Dietvorst et al. 2018 (same authors) and vs.
Dietvorst & Bharti 2020 (a third Dietvorst paper, added in v2; relevant, not
gold, because it postdates the source).

Every statement that cites a pair paper is judged, with no cap. These are
listed under `pair_claims` in `judgments.json` and come on top of the seeded
random sample that `claim_support_rate` uses. The v1 pilot produced 30 of
them. The pair papers are always in the judge's context. Turn 4 asks the
agent to say what each pair paper found.

Two rules affect how these labels read:
- **A "misattributed" label must name the paper.** It needs a `correct_id`
  for a paper the judge was shown. Without one, the statement is re-judged
  once; if still without one, it counts as unsupported (`rejudged`,
  `invalid_misattribution`). In v1 one such label (a Meehl quote cited to
  Sines 1970, whose rationale said the claim was supported) would otherwise
  have counted as a misattribution.
- **Claims citing a title-only record are marked `weak_check`.** These are
  Sniezek & Buckley 1995, Dzindolet 2003, Li 2008, Kawaguchi 2021 and the
  retraction notices.

A claim credited to a journal record but worded from its SSRN version (or the
reverse) counts as supported, marked `relabelled_from: misattributed`. Citing
the working paper instead of the article is scored as a status problem
instead (`trap_flag_rate`, `bd_status_ignored`).

### Natural look-alikes in the corpus

These are real records, kept because a real database has them:
- an OSF preregistration titled "Overcoming algorithm aversion" (2023), a
  replication of Dietvorst 2018 (neutral);
- a 2023 book chapter titled "Algorithm Aversion" (relevant);
- Logg's 2016 dissertation, "When do people rely on algorithms" (relevant);
- Dietvorst & Bartels 2022 and Dietvorst & Bharti 2020, two more Dietvorst
  papers (relevant; the second is also a pair paper).

Publication years follow OpenAlex, which gives online-first years: Dietvorst
2015 appears as 2014 and Dietvorst 2018 as 2016. The SSRN version of the 2018
article is dated 2015. "Dietvorst 2015" is ambiguous in the real literature
too. The judge checks content, not years.

### Neutral labels

70 of the 256 papers are labelled **neutral** in `corpus/labels.json`:
- **Retraction notices** (3).
- **Adjacent literatures:**
  - trust in automation from human factors;
  - advice taking with human advisors only;
  - technology acceptance;
  - fairness perceptions of algorithmic decisions;
  - trust in recommender systems.
- **Domain-specific clinical-vs-actuarial accuracy studies,** for example
  violence prediction and jaundice diagnosis. General reviews of that
  literature are relevant.
- **Non-English papers on algorithm aversion** (German, Spanish, Korean):
  on topic, but unlikely in an English related-work section.
- **OSF study records** (preregistrations and data) that are not papers.

Citing a neutral paper lowers `precision_set` but changes no breakdown flag.
Two gold papers (Sniezek & Buckley 1995; Soll & Larrick 2009) belong to the
human-advisor advice-taking literature, which is otherwise neutral. They are
gold because the source cites them for the reliance paradigm, and they are
flagged `unsure` for review.

### Source references left out of the gold set

Castelo et al. 2019 has 57 references. These were not used as gold:
- the mechanism literature (mind perception, dehumanization, affect, construal
  level);
- e-commerce trust and technology acceptance (two of these are in the corpus
  as neutral);
- diffusion and agency theory;
- eight news articles;
- two books (Meehl 1954; O'Neil 2016).

### Retracted traps

All three traps are real retractions from 2022–2023 on reliance on algorithms
or AI. Each has its real notice (Crossref), whose title says "Retraction".
These retractions are much less publicised than case 1's ivermectin
retractions, so a flag is less likely to come from training data.
`trap_evidence` in `judgments.json` records whether the agent saw the notice.
