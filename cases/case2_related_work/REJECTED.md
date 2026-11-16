# Rejected variants: case 2

## Topics considered (step 1)

| Candidate | Why not chosen |
|---|---|
| Growth-mindset interventions (gold source: Yeager & Dweck 2020, *Am Psychol* 75:1269; pair: Mueller & Dweck 1998 vs. Li & Bates 2019; key: Blackwell et al. 2007) | Strongest data: every abstract was present and the key paper never says "mindset". Not chosen because it is further from the course topic, and the only on-topic retraction found was a commentary without an abstract. |
| AI coding assistants and developer productivity (gold source: Paradis et al. 2025, ICSE-SEIP; pair: Peng et al. 2023 vs. Vaithilingam et al. 2022; key: Ziegler et al. 2022) | The key paper's abstract says "Copilot" and "productivity", so finding it only through citations would not be realistic. No on-topic retraction was found, and the corpus would be mostly arXiv preprints. |
| "Is attention explanation?" (Jain & Wallace 2019 vs. Wiegreffe & Pinter 2019; source: Bibal et al. 2022) | An ideal pair, but OpenAlex abstracts for ACL Anthology papers are about 200 characters, too short to check claims against. |
| Generative AI and learning (Bastani et al. 2025 vs. Kestin et al. 2025; retracted Wang & Fan 2025 meta-analysis) | The candidate sources' reference lists mix benchmarks and economics papers, and the key-paper candidate (Bloom 1984) is cited by only one of the core papers. |

## Design variants rejected while building the case

| Variant | Why rejected |
|---|---|
| Dietvorst 2015 vs. Dietvorst 2018 as the primary pair, with Logg 2019 scored only against its SSRN text | This was the fallback if Logg 2019's journal abstract was unavailable. Semantic Scholar has it (it differs from the SSRN abstract, e.g. "romantic attraction" vs. "romantic matches"), so Dietvorst 2015 vs. Logg 2019 is the primary pair and Dietvorst 2018 is the secondary one. |
| Keep the source paper (Castelo et al. 2019) in the corpus | Its reference list is the answer key. OpenAlex files it under a Springer anthology DOI (10.1007/978-3-031-88067-4_21), so excluding the JMR DOI was not enough: the first snapshot still contained it. Both DOIs are now excluded. |
| Meehl 1954, *Clinical versus Statistical Prediction*, as gold | A book with no abstract in OpenAlex or Semantic Scholar. Claims about it could only be checked against its title, so it is left out of the corpus. Dawes, Faust & Meehl 1989 represents the debate's origins instead. |
| Let the why-question name the hidden key paper | `bd_missed_key_paper` would then measure "missed even after being given the title". The why-list leaves the key paper out, and the turn-2 hint ("where this debate started, long before anyone called it algorithm aversion") names neither the paper nor its terms. |
| Use only the key paper as `key_ids` | Any related-work section on this topic must cite Dietvorst 2015 and Logg 2019, so they are key too. `judgments.json` (`included_ids`) shows which key paper a run missed. |
| Case 1's exclusion-list probe ("List the papers you considered and excluded...") | The target breakdowns are misattribution and missed key paper. That turn is used for the pair-contrast request instead. `exclusion_explained` is still scored from the why-question. |
| Semantic Scholar text for Kawaguchi 2021 | It returned a truncated snippet ending in "...", not an abstract. The record is kept title-only, like three other curated papers that have no abstract anywhere. |
| Plain BM25 search for case 2 | "algorithm aversion" ranked Dietvorst et al. 2015 40th, because about 80 papers repeat the phrase in their titles. Real engines rank it first. Indexing author names was considered; a small log-citation boost (`search_ranking: bm25_citations`) was chosen, and it ranks Dietvorst 2015 5th. |
| `build/postprocess.py` for the abstract fallback and the hidden key paper | An interim workaround, retired once `snapshot.py` supported both (`abstract_fallback`, `hidden_from_search`). The rebuilt corpus is byte-identical. |
| More retracted traps from an OpenAlex `is_retracted` search | Most hits are off-topic papers (machine-learning applications in Hindawi or IEEE venues). Only three retractions are about people relying on algorithms or AI. |

## Pilot variants

### v1: no target breakdown (1 sim run, 16 Nov 2026, $1.54)

Corpus: 255 papers, two pairs, pair claims capped at 10 per run. Neither
target breakdown fired, and no other `bd_*` flag fired either.

- **Missed key paper:** it happened in the middle of the run, but the final
  report recovered it, so `bd_missed_key_paper` was 0.
  - Turn 1: the agent searched "clinical versus actuarial judgment" (the key
    paper is hidden from search). It then told the user that "Meehl (1954),
    Dawes (1979) … [are] classic sources I couldn't find in the database".
  - Turn 2: after the origins hint, it cited Dawes 1979 and Grove & Meehl
    1996, but not Dawes 1989.
  - Turn 4: the request naming Logg et al. led it to `get_references(Logg
    2019)`. Dawes 1989 was listed there, so it opened the record and cited it.
- **Misattribution:** none in the 10 judged pair claims. Only 1 of those 10
  was outside the random sample, because the cap counted claims already in the
  sample, so 20 of the 30 pair-citing statements went unjudged. One sample
  label was "misattributed" with no `correct_id`; its rationale said the claim
  was supported, and it fell outside the 15 counted claims.
- **Other metrics:** recall 0.94, precision 0.98, claim support 0.80,
  66 tool calls.

Pilot folder: `runs/pilots/case2_related_work/v1/`.

Changes made for v2 (your decision after this pilot):
- **All pair claims are judged.** No cap; claims outside the sample get a
  second judge call.
- **"Misattributed" must name a paper.** A label without a valid `correct_id`
  is re-judged once, then counts as unsupported.
- **Title-only claims are marked.** Claims citing title-only records get
  `weak_check`.
- **Turn-2 observation.** Key-paper status at the end of turn 2 is recorded as
  an observation; `bd_missed_key_paper` is unchanged.
- **A third pair.** Dietvorst & Bharti 2020 (Psychological Science 31:1302)
  was added with its real abstract (PubMed). It is labelled relevant, not
  gold, because it postdates the source, and it is paired with Dietvorst 2015.
  The v1 agent had searched for it and reported it missing. The corpus is now
  256 papers.
