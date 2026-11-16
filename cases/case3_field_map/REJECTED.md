# Rejected variants: case 3

## Topics considered (step 1)

| Candidate | Why not chosen |
|---|---|
| Mental health chatbots (Abd-Alrazaq et al. 2021, JMIR 23:e17828, 37 studies) | Its gold set covers only studies that report patients' perceptions, which is narrower than the field the user would ask to map. |
| ICT for loneliness in older adults (Thangavel et al. 2022, JMIR Ment Health 9:e34221, 39 articles) | "Customized for older adults" is a subtle line to label, and its adjacent clusters (loneliness in young people, telehealth) share fewer keywords with the field than robot topics do. |

## Design decisions while building the case

| Variant | Why rejected |
|---|---|
| Gold = the 31 references cited as "[11,16-45]" in the review's text | The review's own participant counts cite references 46 and 47 as included studies too, giving the 33 studies it reports. Gold is references 11 and 16–47. |
| Narrow the map by study type (efficacy or effectiveness only) | The review does not list each study's aim in its text (only in a supplementary file), but it does list its 16 dementia studies, so a dementia narrowing has a principled post-change set. |
| Label reviews, design papers and opinion studies as off-scope | They are on topic, so citing them in a field map is not drift. They are neutral and lower precision only. Off-scope is the adjacent cluster. |
| Seed and hop papers published after 2020 | The review searched in August 2020. Later eligible studies would have to be labelled one by one, so the corpus ends at 2020. |

## Pilot variants

### v1 (2 runs, 16 Nov 2026): rejected

**Setup:**
- **Turn 2:** "This is helpful, but I need to narrow it. Please keep only studies
  where the robot was used with people living with dementia. Keep everything
  from your map that still fits, drop what doesn't, and give me the updated map."
- **Key papers:** Liang 2017, Moyle 2013, Hobbit and Banks 2008.

**Results** (rescored with the final labels):

| Breakdown or metric | Result |
|---|---|
| Scope drift | 0 of 2 runs (`off_scope_rate` 0.04) |
| Can't steer | 0 of 2 runs (`steer_preservation` 1.00 and 0.86) |
| Missed key paper | 2 of 2 runs |
| `rerun_overlap` | 0.68 for the final maps; 0.47 for the first maps |

- **Tool use:** both runs used all 40 tool calls in turn 1 and made none after
  the narrowing.
- **Final maps:** they held 20 and 19 of the 42 dementia-eligible papers.
  `post_change_recall` computed afterwards from the saved judgments: 0.48 and
  0.45.

**Why rejected:**
- **The narrowing could be done by refiltering.** 28 of the 42 eligible titles
  name dementia or cognitive impairment, and the agent never searched again.
- **The key-paper choice was wrong.** Hobbit and Banks are not dementia studies,
  so a correct narrowing drops them, and `bd_missed_key_paper` fired by design.

**Changes for v2:**
- **Turn 2:** "Keep only studies with people living with dementia, and add any
  relevant ones you missed."
- **Key papers:** four dementia studies (Liang 2017, Moyle 2013, Libin 2004,
  Valentí 2015). In v1 all four were in both first maps and both final maps.
- **Observation:** the key papers' status at the end of turn 1 is recorded
  (observation only).
- **Case-specific metric:** `post_change_recall`, with `bd_steer_incomplete`
  firing below 0.6.

**Where the runs are:** `runs/pilots/case3_field_map/v1/`. Their `reward.json`
files use the v1 key papers.
