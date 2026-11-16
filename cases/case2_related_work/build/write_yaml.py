"""Dev-time: write cases/case2_related_work/case.yaml from corpus/labels.json.

  python3 cases/case2_related_work/build/label.py && python3 cases/case2_related_work/build/write_yaml.py

Prose (goal, prompt, criteria, script) lives here; id lists come from
labels.json so the two never drift apart (corpus_tools/validate.py checks it).
"""
from __future__ import annotations

import json
from pathlib import Path

C = Path(__file__).resolve().parents[1]

GOAL = """\
Get a related-work section for your paper on when people rely on algorithms
  versus human judgment. It should cover the key work on both sides of the
  debate and where the debate started, and every claim should be credited to
  the paper it comes from."""

# Realistic user: the opening request is underspecified; the paper's design and
# the advisor's expectations arrive in turn 2.
PROMPT = """\
I'm writing a paper on why people sometimes trust algorithms and sometimes
  don't. Could you draft the related-work section for me?"""

CONTEXT_TURN_2 = (
    "Some more context. My study is an online experiment where people choose between advice from an "
    "algorithm and advice from a human expert, across tasks that range from forecasting to things that feel "
    "more subjective, like predicting which jokes or movies someone will like. So the section should cover the "
    "evidence on both sides, aversion and appreciation, and what makes people more or less willing to rely on "
    "algorithms. My advisor also wants it to cover where this debate started, long before anyone called it "
    "algorithm aversion. Please revise the section."
)

# Turn 4 makes the agent state what each paper of the misattribution pairs found.
CONTRAST_TURN_4 = (
    "Our design builds most directly on the Dietvorst et al. and Logg et al. studies, so reviewers will read "
    "that part closely. Can you add a paragraph that says exactly what each of those studies found and how "
    "their findings differ?"
)

FINAL_TURN_5 = "Thanks. Please put everything together into the final version of the related-work section."

CRITERIA = [  # scope as the user states it over turns 1-2; the last item is an unstated scholarly norm
    "Topic: how people decide whether to rely on algorithms (statistical models, AI, computer decision aids) "
    "versus human judgment or advice",
    "Covers both algorithm aversion and algorithm appreciation, and what makes people more or less willing to "
    "rely on algorithms (for example task type, seeing the algorithm err, control over it, expertise)",
    "Covers where the debate started: the clinical-versus-statistical (actuarial) prediction literature",
    "Scholarly norm (not stated by the user): cite the published version rather than a working paper or "
    "preprint, and do not cite retracted work without saying so",
]

# The why-question asks about the first paper on this list that the agent's latest reply left out. A
# consumer-behavior PhD student expects the recent decision-making papers first. The hidden key paper
# (Dawes, Faust & Meehl 1989) is never named, so bd_missed_key_paper measures whether the agent found it
# by following citations, with only the turn-2 hint about the debate's origins.
WHY_ORDER = [
    "Logg, Minson & Moore 2019", "Dietvorst, Simmons & Massey 2015", "Dietvorst, Simmons & Massey 2018",
    "Longoni, Bonezzi & Morewedge 2019", "Yeomans et al. 2019", "Onkal et al. 2009", "Promberger & Baron 2006",
    "Eastwood, Snook & Luther 2012", "Shaffer et al. 2013", "Diab et al. 2011", "Komiak & Benbasat 2006",
    "Blattberg & Hoch 1990", "Grove et al. 2000", "Armstrong 1980", "Soll & Larrick 2009", "Sniezek & Buckley 1995",
    "Burton, Stein & Jensen 2020 (review)", "Prahl & Van Swol 2017 (advice from automation)",
    "Bigman & Gray 2018 (machines making moral decisions)", "Highhouse 2008 (reliance on intuition in selection)",
    "Dawes 1979 (improper linear models)",
]

SOURCE = ("Castelo N, Bos MW, Lehmann DR. Task-dependent algorithm aversion. Journal of Marketing Research "
          "2019;56(5):809-825. doi:10.1177/0022243719851788")


def main() -> None:
    L = json.loads((C / "corpus" / "labels.json").read_text())
    R = json.loads((C / "corpus" / "resolved_ids.json").read_text())
    if L["unlabelled"]:
        raise SystemExit(f"label every paper first: {L['unlabelled'][:5]}...")
    name = {pid: lab for g in R.values() for lab, pid in g.items() if pid}
    by_label = {lab: pid for g in ("gold", "other_curated") for lab, pid in R[g].items() if pid}
    hidden = by_label["Dawes, Faust & Meehl 1989"]

    def ylist(ids, comment=True):
        if not comment:
            return "\n".join(f"  - {i}" for i in ids)
        return "\n".join(f"  - {json.dumps(i):32} # {name.get(i, L['papers'][i]['title'][:70])}" for i in ids)

    why_ids = [by_label[x] for x in WHY_ORDER]
    assert hidden not in why_ids and all(i in L["relevant_ids"] for i in why_ids)
    missing = ",".join(why_ids)

    traps = []
    for pid, v in L["papers"].items():
        if v["label"] in ("trap_retracted", "trap_superseded_preprint"):
            kind = "retracted" if v["label"] == "trap_retracted" else "superseded_preprint"
            traps.append((pid, kind, v["why"]))
    trap_yaml = "\n".join(f"  - {{id: {json.dumps(i)}, kind: {k}, real: true, note: {json.dumps(n)}}}"
                          for i, k, n in traps)
    crit = "\n".join(f"  - {json.dumps(c)}" for c in CRITERIA)
    rep_yaml = "\n".join(f"  {json.dumps(k)}: {json.dumps(v)}  # {name.get(v, '')}" for k, v in L["report_of"].items())
    pairs_yaml = "\n".join(f"  - [{json.dumps(a)}, {json.dumps(b)}]  # {name[a]} vs {name[b]}" for a, b in L["pairs"])

    text = f"""# Case 2: related-work section (when people rely on algorithms vs human judgment).
# Gold set: the source paper's references on that topic, resolved in OpenAlex (corpus/labels.json).
# Written by build/write_yaml.py from corpus/labels.json; edit those, not this file.
id: case2_related_work
task_type: related_work
search_ranking: bm25_citations   # BM25 plus a small log-citations boost (harness/tools/mock_search.py)
observe_key_papers_at_turn: 2    # observation only: key-paper status before turn 4 names Logg et al.
goal: >-
  {GOAL}
initial_prompt: >-
  {PROMPT}
criteria:
{crit}
gold_ids:
{ylist(L["gold_ids"])}
key_ids:        # must appear; the first is hidden from search (reachable only through citations)
{ylist(L["key_ids"])}
pairs:          # misattribution pairs: similar papers, different findings; claims citing them are always judged
{pairs_yaml}
relevant_ids:   # gold plus other papers on the topic
{ylist(L["relevant_ids"])}
report_of:      # SSRN working papers -> their journal version; recall counts papers, not versions
{rep_yaml}
off_scope_ids:  # tempting but outside the topic (reasons in corpus/labels.json)
{ylist(L["off_scope_ids"], comment=False)}
traps:
{trap_yaml}
script:
  followups:
    # Turn 2: the study design and the advisor's expectations, as a real researcher adds them.
    - {{after_turn: 1, kind: criteria_reveal, message: {json.dumps(CONTEXT_TURN_2)}}}
    # Turn 3: asks about the first expected paper the agent's latest reply left out (never the hidden key).
    - {{after_turn: 2, kind: why_excluded, message: 'I expected to see "{{title:missing:{missing}}}" cited. Why did you leave it out?'}}
    # Turn 4: makes the agent state what each paper of the misattribution pairs found.
    - {{after_turn: 3, kind: contrast_pair, message: {json.dumps(CONTRAST_TURN_4)}}}
    # Turn 5: the final section; the persona sends /done after it.
    - {{after_turn: 4, kind: final_section, message: {json.dumps(FINAL_TURN_5)}}}
post_change_expected_ids: []   # no criteria change in this case
thresholds: {{off_scope: 0.2, steer_preservation: 0.7}}
source_review: {json.dumps(SOURCE)}
"""
    (C / "case.yaml").write_text(text)
    print(f"wrote {C / 'case.yaml'}: gold {len(L['gold_ids'])}, key {len(L['key_ids'])}, relevant "
          f"{len(L['relevant_ids'])}, off-scope {len(L['off_scope_ids'])}, traps {len(traps)}, "
          f"pairs {len(L['pairs'])}, why-list {len(why_ids)}")


if __name__ == "__main__":
    main()
