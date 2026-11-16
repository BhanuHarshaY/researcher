"""Dev-time: write cases/case3_field_map/case.yaml from corpus/labels.json.

  python3 -m corpus_tools.label_case3 && python3 -m corpus_tools.write_case3_yaml
"""
from __future__ import annotations

import json
from pathlib import Path

C = Path("cases/case3_field_map")

GOAL = """\
Get a map of the research on social robots used with older people, then narrow
  it to people living with dementia without losing the work that still fits."""

PROMPT = """\
I'm starting a project on social robots for older people. Can you map the
  research for me: which robots have been studied, with whom and in what
  settings, and what the studies found? I'm interested in studies where a
  social robot was actually used with older people."""

STEER = "Keep only studies with people living with dementia, and add any relevant ones you missed."
ASK_DROPPED = "Which papers from your first map did you drop, and why?"

CRITERIA = [
    "A social robot physically used with older people (65 or over) in an experimental or clinical study",
    "Any setting except acute hospital care",
    "Not: reviews, conference abstracts, case studies, design or development reports only, or opinions without interaction",
    "Not: telepresence robots that only make video calls; rehabilitation, assistive or surgical robots; robots for children",
    "After turn 2: participants are people living with dementia",
]

SOURCE = ("Mahmoudi Asl A, Molinari Ulate M, Franco Martin M, van der Roest H. Methodologies Used to Study the "
          "Feasibility, Usability, Efficacy, and Effectiveness of Social Robots For Elderly Adults: Scoping Review. "
          "J Med Internet Res 2022;24(8):e37434. doi:10.2196/37434")


def main() -> None:
    L = json.loads((C / "corpus" / "labels.json").read_text())
    if L["unlabelled"]:
        raise SystemExit(f"label every paper first: {L['unlabelled'][:5]}")
    name = {k: v["title"][:70] for k, v in L["papers"].items()}

    def ylist(ids, comment=True):
        if not comment:
            return "\n".join(f"  - {i}" for i in ids)
        return "\n".join(f"  - {json.dumps(i):16} # {name.get(i, '')}" for i in ids)

    text = f"""# Case 3: map a field (social robots for older people), then steer it to dementia.
# Gold set: the 33 studies included by the scoping review below, resolved in OpenAlex.
# Written by corpus_tools/write_case3_yaml.py from corpus/labels.json; edit those, not this file.
id: case3_field_map
task_type: field_map
# Search ranking: BM25 with a small boost for papers cited more often (see harness/tools/mock_search.py).
# Chosen after a ranking check: under plain bm25 only 8 of 33 gold papers reached the top 20 for natural queries.
search_ranking: bm25_citations
goal: >-
  {GOAL}
initial_prompt: >-
  {PROMPT}
criteria:
{chr(10).join(f"  - {json.dumps(c)}" for c in CRITERIA)}
gold_ids:
{ylist(L["gold_ids"])}
key_ids:        # all four are dementia studies, so they stay valid after the turn-2 narrowing
{ylist(L["key_ids"])}
# Observation only (judgments.json): were the key papers in the first map, before the narrowing?
observe_key_papers_at_turn: 1
relevant_ids:   # gold plus other studies that meet the criteria (reasons in corpus/labels.json)
{ylist(L["relevant_ids"], comment=False)}
off_scope_ids:  # the adjacent cluster: rehabilitation/assistive/surgical robots, exoskeletons,
                # telepresence-only robots, robots for children or autism, smart homes without robots
{ylist(L["off_scope_ids"], comment=False)}
traps: []       # no retracted papers or superseded preprints in this corpus
script:
  followups:
    # Turn 2: the scripted criteria change (steer_preservation, and post_change_recall below).
    - {{after_turn: 1, kind: criteria_change, message: {json.dumps(STEER)}}}
    # Turn 3: asks what was dropped (not scored; shows whether the agent can account for the change).
    - {{after_turn: 2, kind: other, message: {json.dumps(ASK_DROPPED)}}}
post_change_expected_ids:   # still valid after turn 2: gold and relevant studies with people with dementia
{ylist(L["post_change_expected_ids"], comment=False)}
# Case-specific extra metric (reward.json "case_metrics"; core metrics unchanged):
# post_change_recall = final map ∩ post_change_expected_ids ÷ post_change_expected_ids,
# and bd_steer_incomplete = 1 if it is below its threshold.
case_metrics: [post_change_recall]
thresholds: {{off_scope: 0.2, steer_preservation: 0.7, post_change_recall: 0.6}}
source_review: {json.dumps(SOURCE)}
"""
    (C / "case.yaml").write_text(text)
    print(f"wrote {C / 'case.yaml'}: gold {len(L['gold_ids'])}, key {len(L['key_ids'])}, relevant {len(L['relevant_ids'])}, "
          f"off-scope {len(L['off_scope_ids'])}, post-change {len(L['post_change_expected_ids'])}")


if __name__ == "__main__":
    main()
