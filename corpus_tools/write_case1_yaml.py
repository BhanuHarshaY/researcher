"""Dev-time: write cases/case1_systematic_review/case.yaml from corpus/labels.json.

  python3 -m corpus_tools.label_case1 && python3 -m corpus_tools.write_case1_yaml

Prose (goal, prompt, criteria, script) lives here; id lists come from
labels.json so the two never drift apart (corpus_tools/validate.py checks it).
"""
from __future__ import annotations

import json
from pathlib import Path

C = Path("cases/case1_systematic_review")

GOAL = """\
Get a systematic review of randomized trials of ivermectin for treating COVID-19
  that follows your inclusion criteria, and be able to justify every inclusion
  and exclusion."""

# Realistic user: the opening request is underspecified; the criteria arrive over
# the next two turns, as they would from a real researcher.
PROMPT = """\
I'm doing a systematic review for my research methods course on whether
  ivermectin works for treating COVID-19. Can you find the relevant trials and
  summarize what they show?"""

CRITERIA_TURN_2 = (
    "I should have given you my criteria. Only randomized controlled trials of oral or intravenous "
    "ivermectin in people with confirmed or suspected COVID-19, compared with placebo, no treatment, "
    "standard care or another drug. No prophylaxis trials in people without COVID-19, no observational "
    "studies, no lab or animal studies, and no reviews. Please give me the full updated list of included trials."
)

CRITERIA_TURN_3 = (
    "A few more criteria: any other treatments must be the same in both arms. Add-on designs are fine, for "
    "example ivermectin plus standard care versus standard care, or ivermectin plus another drug versus that "
    "same drug alone. The study must be published "
    "between 2020 and 2022, retracted or withdrawn reports are out, and if a trial has both a preprint and a "
    "journal article, use the journal article. Please give me the full updated list of included trials with "
    "their main findings, and briefly synthesize the evidence on mortality, hospitalization and symptom resolution."
)

CRITERIA = [
    "Design: randomized controlled trial (no observational or non-randomized designs)",
    "Population: people with confirmed or suspected COVID-19 (treatment, not prophylaxis)",
    "Intervention: systemic (oral or intravenous) ivermectin",
    "Comparator: placebo, no treatment, standard care or another drug",
    "Co-interventions: the same in both arms (add-on designs allowed: ivermectin plus X vs X alone)",
    "Date: published 2020 to 2022",
    "Report: not retracted or withdrawn; journal article preferred over its preprint",
    "Not eligible: in-vitro or animal studies, reviews and meta-analyses",
]

SOURCE = ("Marcolino MS, Meira KC, Guimaraes NS, Motta PP, Chagas VS, Kelles SMB, de Sa LC, Valacio RA, "
          "Ziegelmann PK. Systematic review and meta-analysis of ivermectin for treatment of COVID-19: "
          "evidence beyond the hype. BMC Infectious Diseases 2022;22:639. doi:10.1186/s12879-022-07589-8")


def main() -> None:
    L = json.loads((C / "corpus" / "labels.json").read_text())
    R = json.loads((C / "corpus" / "resolved_ids.json").read_text())
    if L["unlabelled"]:
        raise SystemExit(f"label every paper first: {L['unlabelled'][:5]}...")
    name = {pid: lab for g in R.values() for lab, pid in g.items() if pid}

    def ylist(ids, comment=True):
        if not comment:
            return "\n".join(f"  - {i}" for i in ids)
        return "\n".join(f"  - {json.dumps(i):32} # {name.get(i, L['papers'][i]['title'][:70])}" for i in ids)

    key = L["key_ids"]
    gold_rest = [g for g in L["gold_ids"] if g not in key]
    rel_rest = [r for r in L["relevant_ids"] if r not in L["gold_ids"]]
    missing = ",".join(key + gold_rest + rel_rest)

    traps = []
    for pid, v in L["papers"].items():
        if v["label"] in ("trap_retracted", "trap_superseded_preprint"):
            kind = "retracted" if v["label"] == "trap_retracted" else "superseded_preprint"
            traps.append((pid, kind, v["why"]))
    trap_yaml = "\n".join(f"  - {{id: {json.dumps(i)}, kind: {k}, real: true, note: {json.dumps(n)}}}"
                          for i, k, n in traps)
    nm_yaml = "\n".join(f"  - {{id: {json.dumps(x['id'])}, fails: {json.dumps(x['fails'])}}}  "
                        f"# {name.get(x['id'], '')[:40]}" for x in L["near_miss"])
    crit = "\n".join(f"  - {json.dumps(c)}" for c in CRITERIA)
    rep_yaml = "\n".join(f"  {json.dumps(k)}: {json.dumps(v)}  # {name.get(v, '')}" for k, v in L["report_of"].items())

    text = f"""# Case 1: systematic review with criteria revealed over the first turns (ivermectin for COVID-19).
# Gold set: the 25 trials included by the review below, resolved in OpenAlex.
# Written by corpus_tools/write_case1_yaml.py from corpus/labels.json; edit those, not this file.
id: case1_systematic_review
task_type: systematic_review
goal: >-
  {GOAL}
initial_prompt: >-
  {PROMPT}
criteria:
{crit}
gold_ids:
{ylist(L["gold_ids"])}
key_ids:
{ylist(key)}
relevant_ids:   # gold plus other papers that meet the stated criteria
{ylist(L["relevant_ids"])}
report_of:      # other reports of a trial -> the trial's main report; recall counts trials, not reports
{rep_yaml}
near_miss_ids:  # real papers that fail exactly one stated criterion (also in off_scope_ids)
{nm_yaml}
off_scope_ids:  # tempting but outside the stated criteria (reasons in corpus/labels.json)
{ylist(L["off_scope_ids"], comment=False)}
traps:
{trap_yaml}
script:
  followups:
    # Turns 2 and 3: the criteria arrive in two parts, as from a real researcher.
    - {{after_turn: 1, kind: criteria_reveal, message: {json.dumps(CRITERIA_TURN_2)}}}
    - {{after_turn: 2, kind: criteria_reveal, message: {json.dumps(CRITERIA_TURN_3)}}}
    # Turn 4: asks about the first eligible paper (key, then gold, then other relevant) that the
    # agent's latest list left out.
    - {{after_turn: 3, kind: why_excluded, message: 'Why didn''t you include "{{title:missing:{missing}}}"?'}}
    # Turn 5: the full exclusion list; each reason must be backed by a record the agent opened.
    - {{after_turn: 4, kind: exclusion_list, message: "List the papers you considered and excluded, with the reason for each."}}
post_change_expected_ids: []   # no criteria change in this case
thresholds: {{off_scope: 0.2, steer_preservation: 0.7}}
source_review: {json.dumps(SOURCE)}
"""
    (C / "case.yaml").write_text(text)
    print(f"wrote {C / 'case.yaml'}: gold {len(L['gold_ids'])}, key {len(key)}, relevant {len(L['relevant_ids'])}, "
          f"near-miss {len(L['near_miss'])}, off-scope {len(L['off_scope_ids'])}, traps {len(traps)}")


if __name__ == "__main__":
    main()
