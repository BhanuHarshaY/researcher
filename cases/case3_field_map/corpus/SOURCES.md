# Corpus sources: case3_field_map

Built 2026-11-16 with `python3 -m corpus_tools.snapshot cases/case3_field_map/corpus/snapshot.json`.
Frozen after that: run-time search never calls these services.

Sources: OpenAlex (metadata, retraction flags, references), PubMed E-utilities (structured abstracts as passages), Crossref (preprints that OpenAlex merges into journal versions).

- Papers: **286** (published: 286)
- Passages from PubMed structured abstracts: 94
- Seed/hop date window: 2000-01-01 to 2020-12-31 (curated papers are kept regardless)
- Title prefixes stripped (status is shown only by get_paper): RETRACTED:, RETRACTED ARTICLE:, WITHDRAWN:
- Excluded DOI prefixes: 10.2196/37434

## Seed queries (OpenAlex relevance order)

| Query | Returned | New papers |
|---|---|---|
| social robot older adults | 60 | 41 |
| companion robot dementia | 40 | 26 |
| PARO robot seal | 25 | 14 |
| socially assistive robot elderly | 40 | 32 |
| robot nursing home residents | 30 | 16 |
| service robot independent living older people home | 25 | 17 |
| rehabilitation robot older adults | 20 | 13 |
| exoskeleton elderly walking | 12 | 10 |
| telepresence robot older adults | 15 | 11 |
| social robot children autism | 20 | 13 |
| robot-assisted surgery elderly patients | 8 | 1 |
| smart home sensors elderly monitoring | 12 | 10 |

One hop from gold (references and citing papers mentioning 'robot'): 264 new papers.

## gold

| Label | Corpus id | Status | Title |
|---|---|---|---|
| ref11 (dementia) A robotic coach architecture for elder care (ROCARE) based o | W2519261326 | published | A Robotic Coach Architecture for Elder Care (ROCARE) Based on Multi-User Engagement Models |
| ref16 Results of field trials with a mobile service robot for olde | W2994761079 | published | Results of Field Trials with a Mobile Service Robot for Older Adults in 16 Private Househo |
| ref17 Animal-assisted therapy and loneliness in nursing homes: use | W2132164645 | published | Animal-Assisted Therapy and Loneliness in Nursing Homes: Use of Robotic versus Living Dogs |
| ref18 (dementia) Evaluation of a companion robot for individuals with dementi | W2955051104 | published | Evaluation of a Companion Robot for Individuals With Dementia: Quantitative Findings of th |
| ref19 Older users' acceptance of an assistive robot: attitudinal c | W2757061426 | published | Older users’ acceptance of an assistive robot: Attitudinal changes following brief exposur |
| ref20 Robotic seals as therapeutic tools in an aged care facility: | W2549860918 | published | Robotic Seals as Therapeutic Tools in an Aged Care Facility: A Qualitative Study |
| ref21 Benefits and problems of health-care robots in aged care set | W1945345301 | published | Benefits and problems of health‐care robots in aged care settings: A comparison trial |
| ref22 Robotic services acceptance in smart environments with older | W2811507747 | published | Robotic Services Acceptance in Smart Environments With Older Adults: User Satisfaction and |
| ref23 (dementia) Development of a socially believable multi-robot solution fr | W2011941393 | published | Development of a Socially Believable Multi-Robot Solution from Town to Home |
| ref24 (dementia) Service innovation through social robot engagement to improv | W2317990020 | published | Service innovation through social robot engagement to improve dementia care quality |
| ref25 Hobbit, a care robot supporting independent living at home:  | W2294144074 | published | Hobbit, a care robot supporting independent living at home: First prototype and lessons le |
| ref26 Two-year use of care robot Zora in Dutch nursing homes: an e | W2915888239 | published | Two-Year Use of Care Robot Zora in Dutch Nursing Homes: An Evaluation Study |
| ref27 (dementia) Field-based development of an information support robot for  | W1801949096 | published | Field-based development of an information support robot for persons with dementia |
| ref28 Using socially assistive robots for monitoring and preventin | W2939831007 | published | Using socially assistive robots for monitoring and preventing frailty among older adults:  |
| ref29 (dementia) Engagement and experience of older people with socially assi | W2944083468 | published | Engagement and experience of older people with socially assistive robots in home care |
| ref30 (dementia) Human robot engagement and acceptability in residential aged | W2564685734 | published | Human Robot Engagement and Acceptability in Residential Aged Care |
| ref31 (dementia) Effects of intervention using PARO on the cognition, emotion | W2894885829 | published | Effects of Intervention Using PARO on the Cognition, Emotion, Problem Behavior, and Social |
| ref32 (dementia) Comparison of the effect of human interaction, animal-assist | W1972564462 | published | Comparison of the Effect of Human Interaction, Animal-Assisted Therapy, and AIBO-Assisted  |
| ref33 (dementia) A pilot randomized trial of a companion robot for people wit | W2732925385 | published | A Pilot Randomized Trial of a Companion Robot for People With Dementia Living in the Commu |
| ref34 (dementia) Therapeutic robocat for nursing home residents with dementia | W2074069593 | published | Therapeutic robocat for nursing home residents with dementia: Preliminary inquiry |
| ref35 (dementia) Exploring the effect of companion robots on emotional expres | W1488883230 | published | Exploring the Effect of Companion Robots on Emotional Expression in Older Adults with Deme |
| ref36 Enhancing older people’s activity and participation with soc | W2898061611 | published | Enhancing older people’s activity and participation with socially assistive robots: a mult |
| ref37 Social service robots to support independent living : Experi | W2402706188 | published | Social service robots to support independent living: Experiences from a field trial |
| ref38 (dementia) How people with dementia perceive a therapeutic robot called | W2985514812 | published | How people with dementia perceive a therapeutic robot called PARO in relation to their pai |
| ref39 (dementia) Effects of a humanoid socially assistive robot versus tablet | W2975531399 | published | Effects of a Humanoid Socially Assistive Robot Versus Tablet Training on Psychosocial and  |
| ref40 Robot-assisted therapy for improving social interactions and | W1510372641 | published | Robot‐assisted therapy for improving social interactions and activity participation among  |
| ref41 Behavioral responses of nursing home residents to visits fro | W2294211165 | published | Behavioral Responses of Nursing Home Residents to Visits From a Person with a Dog,a Robot  |
| ref42 Evaluation of a companion robot based on field tests with si | W2717439789 | published | Evaluation of a companion robot based on field tests with single older adults in their hom |
| ref43 (dementia) Social robots in advanced dementia | W1807810766 | published | Social robots in advanced dementia |
| ref44 (dementia) Robot assisted activity at a health service facility for the | W1979427169 | published | Robot assisted activity at a health service facility for the aged for ten weeks: An interi |
| ref45 Social and physiological influences of robot therapy in a ca | W1988578580 | published | Social and physiological influences of robot therapy in a care house |
| ref46 Evaluation of a small socially-assistive humanoid robot in i | W2034762802 | published | Evaluation of a Small Socially-Assistive Humanoid Robot in Intelligent Homes for the Care  |
| ref47 Robots in older people’s homes to improve medication adheren | W1558982838 | published | Robots in Older People’s Homes to Improve Medication Adherence and Quality of Life: A Rand |

## crossref_preprints

| Label | Corpus id | Status | Title |
|---|---|---|---|

## openalex_preprints

| Label | Corpus id | Status | Title |
|---|---|---|---|

## retraction_notices

| Label | Corpus id | Status | Title |
|---|---|---|---|

## Dropped records and problems

- dropped duplicate W2040178395 (same title as W4243437205): Use of seal-like robot PARO in sensory group therapy for older adults 
- dropped duplicate W4237388661 (same title as W2120142058): Potential use of robots in Taiwanese nursing homes
- dropped duplicate W4254686839 (same title as W2047271476): Intelligent Interaction For Human-Friendly Service Robot in Smart Hous
- dropped duplicate W2810248467 (same title as W4253064634): A Taxonomy in Robot-Assisted Training: Current Trends, Needs and Chall
