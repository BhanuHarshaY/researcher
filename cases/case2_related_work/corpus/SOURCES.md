# Corpus sources: case2_related_work

Built 2026-11-16 with `python3 -m corpus_tools.snapshot cases/case2_related_work/corpus/snapshot.json`.
Frozen after that: run-time search never calls these services.

Sources: OpenAlex (metadata, retraction flags, references), PubMed E-utilities (structured abstracts as passages), Crossref (preprints that OpenAlex merges into journal versions).

- Papers: **256** (preprint: 14, published: 239, retracted: 3)
- Passages from PubMed structured abstracts: 59
- Seed/hop date window: 1950-01-01 to 2025-12-31 (curated papers are kept regardless)
- Title prefixes stripped (status is shown only by get_paper): RETRACTED:, RETRACTED ARTICLE:, WITHDRAWN:, [Retracted], Retracted:
- Excluded DOI prefixes: 10.1177/0022243719851788, 10.1007/978-3-031-88067-4_21

## Seed queries (OpenAlex relevance order)

| Query | Returned | New papers |
|---|---|---|
| algorithm aversion | 60 | 37 |
| algorithm appreciation | 20 | 11 |
| algorithmic advice | 30 | 20 |
| trust in artificial intelligence advice | 25 | 20 |
| clinical versus actuarial prediction | 15 | 10 |
| advice taking judge advisor system | 12 | 10 |
| medical artificial intelligence patients trust | 15 | 13 |
| trust in automation reliance | 12 | 6 |
| algorithm aversion robo-advisor investment | 10 | 9 |
| recommender system user trust | 10 | 5 |
| algorithmic fairness machine learning | 10 | 7 |
| algorithmic management workers platform | 10 | 8 |

One hop from gold (references and citing papers mentioning 'algorithm'): 63 new papers.

## gold

| Label | Corpus id | Status | Title |
|---|---|---|---|
| Dawes, Faust & Meehl 1989 | W2012218966 | published | Clinical Versus Actuarial Judgment |
| Dietvorst, Simmons & Massey 2015 | W3125633690 | published | Algorithm Aversion: People Erroneously Avoid Algorithms after Seeing Them Err |
| Logg, Minson & Moore 2019 | W2800068874 | published | Algorithm appreciation: People prefer algorithmic to human judgment |
| Dietvorst, Simmons & Massey 2018 | W3121705224 | published | Overcoming Algorithm Aversion: People Will Use Imperfect Algorithms If They Can (Even Slig |
| Grove et al. 2000 | W2168729696 | published | Clinical versus mechanical prediction: A meta-analysis. |
| Longoni, Bonezzi & Morewedge 2019 | W2942858056 | published | Resistance to Medical Artificial Intelligence |
| Yeomans et al. 2019 | W2913854599 | published | Making sense of recommendations |
| Onkal et al. 2009 | W2158570360 | published | The relative influence of advice from human experts and statistical methods on forecast ad |
| Promberger & Baron 2006 | W2070125214 | published | Do patients trust computers? |
| Shaffer et al. 2013 | W2085105383 | published | Why Do Patients Derogate Physicians Who Use a Computer-Based Diagnostic Support System? |
| Eastwood, Snook & Luther 2012 | W2150479185 | published | What People Want From Their Professionals: Attitudes Toward Decision‐making Strategies |
| Diab et al. 2011 | W1522638407 | published | Lay Perceptions of Selection Decision Aids in US and Non-US Samples |
| Blattberg & Hoch 1990 | W2104546629 | published | Database Models and Managerial Intuition: 50% Model + 50% Manager |
| Komiak & Benbasat 2006 | W3144406692 | published | The Effects of Personalization and Familiarity on Trust and Adoption of Recommendation Age |
| Armstrong 1980 | W2137384635 | preprint | The Seer-Sucker Theory: The Value of Experts in Forecasting |
| Sniezek & Buckley 1995 | W2020463305 | published | Cueing and Cognitive Conflict in Judge-Advisor Decision Making |
| Soll & Larrick 2009 | W2032056105 | published | Strategies for revising judgment: How (and how well) people use others’ opinions. |

## traps_retracted

| Label | Corpus id | Status | Title |
|---|---|---|---|
| ChatGPT and algorithm aversion 2023 (PRBM, retracted) | W4386715724 | retracted | A Cogitation on the ChatGPT Craze from the Perspective of Psychological Algorithm Aversion |
| Adolescents' algorithmic resistance 2022 (Front Psychol, retracted) | W4224326502 | retracted | Adolescents’ Algorithmic Resistance to Short Video APP’s Recommendation: The Dual Mediatin |
| AI and human loss in decision making 2023 (HSSC, retracted) | W4380078608 | retracted | Impact of artificial intelligence on human loss in decision making, laziness and safety in |

## other_curated

| Label | Corpus id | Status | Title |
|---|---|---|---|
| Dawes 1979 (improper linear models) | W2056418346 | published | The robust beauty of improper linear models in decision making. |
| Highhouse 2008 (reliance on intuition in selection) | W2171321543 | published | Stubborn Reliance on Intuition and Subjectivity in Employee Selection |
| Dzindolet et al. 2003 (trust in automation reliance) | W2010158189 | published | The role of trust in automation reliance |
| Prahl & Van Swol 2017 (advice from automation) | W2600700815 | published | Understanding algorithm aversion: When is advice from automation discounted? |
| Bigman & Gray 2018 (machines making moral decisions) | W2886363025 | published | People are averse to machines making moral decisions |
| Glikson & Woolley 2020 (review: trust in AI) | W3013998503 | published | Human Trust in Artificial Intelligence: Review of Empirical Research |
| Lee & See 2004 (trust in automation) | W4243342770 | published | Trust in Automation: Designing for Appropriate Reliance |
| Kawaguchi 2021 (workers following an algorithm) | W3036668652 | published | When Will Workers Follow an Algorithm? A Field Experiment with a Retail Business |
| Burton, Stein & Jensen 2020 (review) | W2981686111 | published | A systematic review of algorithm aversion in augmented decision making |
| Mahmud et al. 2022 (review) | W4200546216 | published | What influences algorithmic decision-making? A systematic literature review on algorithm a |
| Jussupow, Benbasat & Heinzl 2020 (review) | W3024435124 | preprint | Why are we averse towards Algorithms? A comprehensive literature Review on Algorithm avers |
| Bogert, Schecter & Watson 2021 | W3152500611 | published | Humans rely more on algorithms than social influence as a task becomes more difficult |
| Dietvorst & Bharti 2020 | W2974452734 | published | People Reject Algorithms in Uncertain Decision Domains Because They Have Diminishing Sensi |
| Davis, Bagozzi & Warshaw 1989 (technology acceptance) | W2033943395 | published | User Acceptance of Computer Technology: A Comparison of Two Theoretical Models |
| Li, Hess & Valacich 2008 (trust in new technology) | W2024981255 | published | Why do we trust new technology? A study of initial trust formation with organizational inf |

## crossref_preprints

| Label | Corpus id | Status | Title |
|---|---|---|---|
| Logg, Minson & Moore SSRN working paper (2017) | 10.2139/ssrn.2941774 | preprint | Algorithm Appreciation: People Prefer Algorithmic To Human Judgment |
| Dietvorst, Simmons & Massey SSRN working paper (2015) of the 2018 article | 10.2139/ssrn.2616787 | preprint | Overcoming Algorithm Aversion: People Will Use Imperfect Algorithms If They Can (Even Slig |

## openalex_preprints

| Label | Corpus id | Status | Title |
|---|---|---|---|

## retraction_notices

| Label | Corpus id | Status | Title |
|---|---|---|---|
| Adolescents’ Algorithmic Resistance to Short Video APP’s Rec | 10.3389/fpsyg.2025.1675601 | published | Retraction: Adolescents' algorithmic resistance to short video APP's recommendation: the d |
| Impact of artificial intelligence on human loss in decision  | 10.1057/s41599-026-06602-8 | published | Retraction Note: Impact of artificial intelligence on human loss in decision making, lazin |
| A Cogitation on the ChatGPT Craze from the Perspective of Ps | 10.2147/prbm.s477151 | published | A Cogitation on the ChatGPT Craze from the Perspective of Psychological Algorithm Aversion |

## Abstract fallback and hidden papers

Abstracts that OpenAlex and PubMed lack come from Semantic Scholar (spec `abstract_fallback`); papers in spec `hidden_from_search` are reachable only through citation links.

- W2010158189 (The role of trust in automation reliance): no abstract in Semantic Scholar; kept without passages
- W2020463305 (Cueing and Cognitive Conflict in Judge-Advisor Decision Maki): no abstract in Semantic Scholar; kept without passages
- W2024981255 (Why do we trust new technology? A study of initial trust for): no abstract in Semantic Scholar; kept without passages
- W2800068874 (Algorithm appreciation: People prefer algorithmic to human j): abstract from Semantic Scholar (frozen in s2_abstracts.json)
- W3036668652 (When Will Workers Follow an Algorithm? A Field Experiment wi): only a truncated snippet in Semantic Scholar; kept without passages
- W2012218966 (Dawes, Faust & Meehl 1989) hidden from keyword search; referenced by 42 searchable papers, e.g. W1001721205, W1987352340, W2020239630, W2070125214, W2102256472, W2104546629

## Dropped records and problems

- dropped notice record W7113913578: Correction to “The Influence of ‘Algorithm Aversion’ and ‘Algorithm Appreciation
- dropped duplicate W2890416412 (same title as W2551317447): Human Decisions and Machine Predictions
- dropped duplicate W3167021722 (same title as W3120272807): Eliciting Human Judgment for Prediction Algorithms
