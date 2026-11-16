# Corpus sources: case1_systematic_review

Built 2026-11-16 with `python3 -m corpus_tools.snapshot cases/case1_systematic_review/corpus/snapshot.json`.
Frozen after that: run-time search never calls these services.

Sources: OpenAlex (metadata, retraction flags, references), PubMed E-utilities (structured abstracts as passages), Crossref (preprints that OpenAlex merges into journal versions).

- Papers: **276** (preprint: 24, published: 246, retracted: 6)
- Passages from PubMed structured abstracts: 171
- Seed/hop date window: 2020-01-01 to 2024-12-31 (curated papers are kept regardless)
- Title prefixes stripped (status is shown only by get_paper): RETRACTED:, RETRACTED ARTICLE:, WITHDRAWN:
- Excluded DOI prefixes: 10.1186/s12879-022-07589-8

## Seed queries (OpenAlex relevance order)

| Query | Returned | New papers |
|---|---|---|
| ivermectin COVID-19 randomized | 70 | 39 |
| ivermectin SARS-CoV-2 | 40 | 27 |
| ivermectin COVID-19 treatment trial | 30 | 4 |
| ivermectin prophylaxis COVID-19 | 20 | 15 |
| ivermectin COVID-19 meta-analysis | 20 | 11 |
| ivermectin COVID-19 observational cohort | 15 | 6 |
| repurposed drugs COVID-19 randomized trial outpatients | 25 | 19 |
| fluvoxamine hydroxychloroquine COVID-19 randomized | 15 | 11 |
| ivermectin scabies onchocerciasis | 10 | 10 |

One hop from gold (references and citing papers mentioning 'ivermectin'): 84 new papers.

## gold

| Label | Corpus id | Status | Title |
|---|---|---|---|
| Ahmed 2020 | W3107056972 | published | A five-day course of ivermectin for the treatment of COVID-19 may reduce the duration of i |
| Babalola 2021 | W3129242298 | published | Ivermectin shows clinical benefits in mild to moderate COVID19: a randomized controlled do |
| Biber 2022 | W4284890619 | published | The effect of ivermectin on the viral load and culture viability in early treatment of non |
| Buonfrate 2022 (COVER) | W4212946211 | published | High-dose ivermectin for early treatment of COVID-19 (COVER study): a randomised, double-b |
| Chaccour 2021 (SAINT) | W3111068209 | published | The effect of early treatment with ivermectin on viral load, symptoms and humoral response |
| Chachar 2020 | W3092176787 | published | Effectiveness of Ivermectin in SARS-CoV-2/COVID-19 Patients |
| Beltran Gonzalez 2022 | W4220768079 | published | Efficacy and Safety of Ivermectin and Hydroxychloroquine in Patients with Severe COVID-19: |
| Krolewiecki 2021 | W3170319714 | published | Antiviral effect of high-dose ivermectin in adults with COVID-19: A proof-of-concept rando |
| Lopez-Medina 2021 | W3135420706 | published | Effect of Ivermectin on Time to Resolution of Symptoms Among Adults With Mild COVID-19: A  |
| Mohan 2021 (RIVET-COV) | W3197929425 | published | Single-dose oral ivermectin in mild and moderate COVID-19 (RIVET-COV): A single-centre ran |
| Ravikirti 2021 | W3182729893 | published | Evaluation of Ivermectin as a Potential Treatment for Mild to Moderate COVID-19: A Double- |
| Vallejos 2021 (IVERCOR) | W3173645873 | published | Ivermectin to prevent hospitalizations in patients with COVID-19 (IVERCOR-COVID19) a rando |
| Reis 2022 (TOGETHER) | W4220754707 | published | Effect of Early Treatment with Ivermectin among Patients with Covid-19 |
| Naggie 2022 (ACTIV-6) | W4307043809 | published | Effect of Ivermectin vs Placebo on Time to Sustained Recovery in Outpatients With Mild to  |
| Abd-Elsalam 2021 | W3164512669 | published | Clinical study evaluating the efficacy of ivermectin in COVID‐19 treatment: A randomized c |
| Bukhari 2021 | W3126179459 | preprint | Efficacy of Ivermectin in COVID-19 Patients with Mild to Moderate Disease |
| Lim 2022 (I-TECH) | W4212973150 | published | Efficacy of Ivermectin Treatment on Disease Progression Among Adults With Mild to Moderate |
| Manomaipiboon 2022 | W4293176350 | published | Efficacy and safety of ivermectin in the treatment of mild to moderate COVID-19 infection: |
| Faisal 2020 | W3161928646 | published | Potential use of azithromycin alone and in combination with ivermectin in fighting against |
| Okumus 2021 | W3130646175 | published | Evaluation of the effectiveness and safety of adding ivermectin to treatment in severe COV |
| Podder 2020 | W3150247726 | published | Outcome of ivermectin treated mild to moderate COVID-19 cases: a single-centre, open-label |
| Shahbaznejad 2021 | W3157727129 | published | Effects of Ivermectin in Patients With COVID-19: A Multicenter, Double-blind, Randomized,  |
| La Rocha 2022 | W4311938754 | published | Ivermectin compared with placebo in the clinical course in Mexican patients with asymptoma |
| Galan 2021 | W3133698266 | published | Phase 2 randomized study on chloroquine, hydroxychloroquine or ivermectin in hospitalized  |
| Niaee 2021 | W3111064783 | published | Ivermectin as an adjunct treatment for hospitalized adult COVID-19 patients: A randomized  |

## traps_retracted

| Label | Corpus id | Status | Title |
|---|---|---|---|
| Pott-Junior 2021 (retracted) | W3134585354 | retracted | Use of ivermectin in the treatment of Covid-19: A pilot trial |
| Samaha 2021 (retracted) | W3164155067 | retracted | Effects of a Single Dose of Ivermectin on Viral and Clinical Outcomes in Asymptomatic SARS |
| Elgazzar 2020 (withdrawn preprint) | W3110602237 | retracted | Efficacy and Safety of Ivermectin for Treatment and prophylaxis of COVID-19 Pandemic |
| IRICT 2022 (RCT, retracted 2024) | W4283838215 | retracted | Ivermectin role in COVID-19 treatment (IRICT): single-center, adaptive, randomized, double |

## near_miss

| Label | Corpus id | Status | Title |
|---|---|---|---|
| Naggie 2023 (ACTIV-6 600) | date: published 2023 | W4321369786 | published | Effect of Higher-Dose Ivermectin for 6 Days vs Placebo on Time to Sustained Recovery in Ou |
| Hayward 2024 (PRINCIPLE) | date: published 2024 | W4392303143 | published | Ivermectin for COVID-19 in adults in the community (PRINCIPLE): An open, randomised, contr |
| Rajter 2021 (ICON) | design: retrospective cohort | W3091860795 | published | Use of Ivermectin Is Associated With Lower Mortality in Hospitalized Patients With Coronav |
| Camprubi 2020 | design: retrospective | W3104739766 | published | Lack of efficacy of standard doses of ivermectin in severe COVID-19 patients |
| Ozer 2021 | design: prospective observational | W3217293035 | published | Effectiveness and safety of Ivermectin in COVID‐19 patients: A prospective study at a safe |
| Gorial 2020 | design: historical control | W3041503566 | preprint | Effectiveness of Ivermectin as add-on Therapy in COVID-19 Management (Pilot Trial) |
| Morgenstern 2020 | design: retrospective | W3102430453 | preprint | The use of compassionate Ivermectin in the management of symptomatic outpatients and hospi |
| Shouman 2021 | population: prophylaxis in uninfected contacts | W3129600723 | published | Use of Ivermectin as a Potential Chemoprophylaxis for COVID-19 in Egypt: A Randomised Clin |
| Aref 2021 | intervention: nasal spray, not systemic | W3168400794 | published | Clinical, Biochemical and Molecular Evaluations of Ivermectin Mucoadhesive Nanosuspension  |
| Mahmud 2021 | co-intervention: doxycycline in ivermectin arm only | W3162891398 | published | Ivermectin in combination with doxycycline for treating COVID-19 symptoms: a randomized tr |
| Hashim 2020 | co-intervention: doxycycline in ivermectin arm only | W4287129885 | published | Controlled Randomized Clinical Trial on Using Ivermectin with Doxycycline for Treating COV |
| Chowdhury 2021 | co-intervention: doxycycline vs azithromycin | W3133633583 | published | A Comparative Study on Ivermectin-Doxycycline and Hydroxychloroquine-Azithromycin Therapy  |

## other_curated

| Label | Corpus id | Status | Title |
|---|---|---|---|
| Kishoria 2020 (eligible RCT not in the review) | W3088905160 | published | IVERMECTIN AS ADJUVANT TO HYDROXYCHOLOROQUINE IN PATIENTS RESISTANT TO STANDARD TREATMENT  |
| Bramante 2022 (COVID-OUT) | W4292148078 | published | Randomized Trial of Metformin, Ivermectin, and Fluvoxamine for Covid-19 |
| Caly 2020 (in vitro) | W3014962324 | published | The FDA-approved drug ivermectin inhibits the replication of SARS-CoV-2 in vitro |
| Popp 2022 (Cochrane review) | W4283205481 | published | Ivermectin for preventing and treating COVID-19 |
| Bryant 2021 (meta-analysis) | W3168908540 | published | Ivermectin for Prevention and Treatment of COVID-19 Infection: A Systematic Review, Meta-a |
| Hill 2021 (meta-analysis, retracted and replaced) | W3121596699 | retracted | Meta-analysis of Randomized Trials of Ivermectin to Treat SARS-CoV-2 Infection |
| Roman 2021 (meta-analysis) | W3174188666 | published | Ivermectin for the Treatment of Coronavirus Disease 2019: A Systematic Review and Meta-ana |
| Izcovich 2022 (systematic review) | W4200397938 | published | Bias as a source of inconsistency in ivermectin trials for COVID-19: A systematic review.  |
| Behera 2020 (case-control) | W3129541046 | published | Role of ivermectin in the prevention of SARS-CoV-2 infection among healthcare workers in I |
| Chahla 2021b (cluster-randomized) | W3159407313 | preprint | Cluster Randomised Trials - Ivermectin Repurposing For COVID-19 Treatment Of Outpatients W |
| Seet 2021 (prophylaxis, active comparators) | W3153015123 | published | Positive impact of oral hydroxychloroquine and povidone-iodine throat spray for COVID-19 p |

## crossref_preprints

| Label | Corpus id | Status | Title |
|---|---|---|---|
| Naggie 2022 (ACTIV-6) medRxiv preprint, interim numbers | 10.1101/2022.06.10.22276252 | preprint | Ivermectin for Treatment of Mild-to-Moderate COVID-19 in the Outpatient Setting: A Decentr |
| Ravikirti 2021 medRxiv preprint | 10.1101/2021.01.05.21249310 | preprint | Ivermectin as a potential treatment for mild to moderate COVID-19 – A double blind randomi |
| Biber 2021 medRxiv preprint | 10.1101/2021.05.31.21258081 | preprint | Favorable outcome on viral load and culture viability using Ivermectin in early treatment  |

## openalex_preprints

| Label | Corpus id | Status | Title |
|---|---|---|---|
| La Rocha 2022 Research Square preprint | W6901825914 | preprint | Ivermectin compared with placebo in the clinical evolution of Mexican patients with asympt |

## retraction_notices

| Label | Corpus id | Status | Title |
|---|---|---|---|
| Efficacy and Safety of Ivermectin for Treatment and prophyla | 10.21203/rs.3.rs-100956/v4 | published | WITHDRAWN: Efficacy and Safety of Ivermectin for Treatment and prophylaxis of COVID-19 Pan |
| Meta-analysis of Randomized Trials of Ivermectin to Treat SA | 10.1093/ofid/ofac056 | published | Retraction to: Meta-analysis of Randomized Trials of Ivermectin to Treat SARS-CoV-2 Infect |
| Use of ivermectin in the treatment of Covid-19: A pilot tria | 10.1016/j.toxrep.2022.04.009 | published | Retraction notice to “Use of ivermectin in the treatment of Covid-19: A pilot trial” [Toxi |
| Effects of a Single Dose of Ivermectin on Viral and Clinical | 10.3390/v13112154 | published | RETRACTED: Samaha et al. Effects of a Single Dose of Ivermectin on Viral and Clinical Outc |
| Ivermectin role in COVID-19 treatment (IRICT): single-center | 10.1080/14787210.2024.2362097 | published | Statement of Retraction: Ivermectin role in COVID-19 treatment (IRICT): single-center, ada |
| Microbiome-Based Hypothesis on Ivermectin’s Mechanism in COV | 10.3389/fmicb.2023.1216170 | published | Retraction: Microbiome-based hypothesis on Ivermectin's mechanism in COVID-19: Ivermectin  |

## Dropped records and problems

- dropped duplicate W3153356117 (same title as W4283205481): Ivermectin for preventing and treating COVID-19
- dropped notice record W4386896238: Erratum: Efficacy and safety of single-dose ivermectin in mild-to-moderate COVID
- dropped notice record W3196470190: Corrigendum to Antiviral effect of high-dose ivermectin in adults with COVID-19:
- dropped duplicate W4206726277 (same title as W4283205481): Ivermectin for preventing and treating COVID-19
- dropped duplicate W4243093711 (same title as W3168908540): Ivermectin for prevention and treatment of COVID-19 infection: a syste
- dropped duplicate W4220960674 (same title as W3159407313): Cluster Randomised Trials - Ivermectin Repurposing for Covid-19 Treatm
- dropped notice record W4285116919: Retraction notice to “Use of ivermectin in the treatment of Covid-19: A pilot tr
- dropped duplicate W4243189714 (same title as W3110602237): Efficacy and Safety of Ivermectin for Treatment and prophylaxis of COV
- dropped duplicate W4251182315 (same title as W3110602237): Efficacy and Safety of Ivermectin for Treatment and prophylaxis of COV
- dropped duplicate W4233034867 (same title as W3158596488): Review of the Emerging Evidence Demonstrating the Efficacy of Ivermect
- dropped duplicate W4244632471 (same title as W3110602237): Efficacy and Safety of Ivermectin for Treatment and prophylaxis of COV
- dropped W4399326861: it is the retraction notice 10.1080/14787210.2024.2362097, re-added from Crossref
