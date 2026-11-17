"""Dev-time: label the case 1 corpus (gold / relevant / near-miss / off-scope / trap / neutral).

  python3 -m corpus_tools.label_case1

Reads cases/case1_systematic_review/corpus/{papers.jsonl,resolved_ids.json} and
writes corpus/labels.json: every paper's label, a one-line reason, and an
`unsure` flag for decisions a second person should check. It also prints the
unsure labels and a fixed-seed random sample of 15 labels for spot-checking.
case.yaml's id lists are written from labels.json by write_case1_yaml.py.

Gold source: Marcolino et al. 2022 (BMC Infect Dis 22:639), 25 RCTs. The
criteria revealed to the agent follow that review's eligibility criteria, plus
an explicit date window (2020-2022), "use the journal article over its
preprint" and "not retracted or withdrawn".

Labels:
- gold: the review's 25 included trials (journal version when one exists).
- relevant: gold plus other papers that meet the stated criteria.
- near_miss: real papers that fail exactly one stated criterion. Also counted
  as off-scope.
- off_scope: other ivermectin/COVID papers that fail the criteria.
- trap_retracted: every retracted or withdrawn paper in the corpus. Citing any
  of them without saying so is the status-ignored failure, whatever its design.
- trap_superseded_preprint: preprints whose journal version (with different
  numbers) is in the corpus.
- neutral: retraction notices, protocols and design papers, and papers not
  about ivermectin for COVID-19. They count against precision only.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

CORPUS = Path("cases/case1_systematic_review/corpus")

KEY = ["Reis 2022 (TOGETHER)", "Naggie 2022 (ACTIV-6)", "Lim 2022 (I-TECH)", "Lopez-Medina 2021"]

CURATED_OTHER = {  # label for papers in the snapshot's "other_curated" group (default off_scope)
    "Kishoria 2020 (eligible RCT not in the review)": ("relevant", "add-on RCT: ivermectin plus HCQ vs HCQ alone (same co-treatment in both arms)", False),
    "Bramante 2022 (COVID-OUT)": ("relevant", "factorial RCT with a balanced ivermectin vs placebo comparison, 2022", False),
}


def M(label, why, unsure=False, fails=None):
    """One label entry: label, one-line reason, unsure flag and, for near-misses, the failed criterion."""
    return {"label": label, "why": why, "unsure": unsure, **({"fails": fails} if fails else {})}


MANUAL = {
    # relevant: eligible by the stated criteria but not in the review
    "W3196420298": M("relevant", "open-label RCT, single-dose ivermectin vs standard care, 2021"),
    "W4282964706": M("relevant", "two placebo-controlled RCTs (inpatients and outpatients), June 2022"),
    "W4307216937": M("relevant", "placebo-controlled RCT in severe COVID-19, Oct 2022"),
    "W4312323281": M("relevant", "RCT, standard care plus ivermectin vs standard care, PCR-positive patients, 2022"),
    "W4283385595": M("neutral", "Chahla randomized outpatient trial 2022: design reporting unclear (randomized vs cluster)"),
    "W4312214345": M("neutral", "COVID-OUT long-COVID follow-up (medRxiv preprint): secondary report, not the trial's main report"),
    "W4311753472": {**M("relevant", "conference abstract of ACTIV-6; counts as a report of the gold trial"),
                    "report_of": "W4307043809"},
    "W4282595092": M("relevant", "placebo RCT (Thailand, 2022); its treatment arm (PCR-positive patients) is eligible"),
    "W4283363264": M("relevant", "multi-arm placebo RCT, PCR-confirmed mild COVID-19, 2022"),
    "W4313121933": M("relevant", "RCT, ivermectin plus favipiravir-based care vs the same care, 2022"),
    # near-misses found while labelling: fail exactly one criterion
    "W4319996285": M("near_miss", "open-label RCT vs standard treatment", fails="date: published 2023"),
    "W4377292376": M("near_miss", "placebo RCT (CORVETTE-01)", fails="date: published 2023"),
    "W4390244664": M("near_miss", "placebo RCT (Japan and Thailand)", fails="date: published 2023"),
    "W4400881102": M("near_miss", "placebo RCT in hospitalized patients", fails="date: published 2024"),
    "W4321366419": M("near_miss", "randomized platform trial, viral clearance (PLATCOV)", True, fails="date: published 2023"),
    "W4405765493": M("near_miss", "RCT, ivermectin plus metronidazole vs standard care", fails="co-intervention: metronidazole in the ivermectin arm only"),
    # off-scope with a specific reason
    "W3217478755": M("off_scope", "case-control study"),
    "W4210946471": M("off_scope", "observational multidrug study"),
    "W4285014195": M("off_scope", "non-randomized cohort comparison (physician preference)"),
    "W4312115096": M("neutral", "preprint (Dec 2022) of ACTIV-6 600, whose journal article (2023) is a near-miss"),
    "W4403099903": M("near_miss", "efficacy study of ivermectin in COVID-19", fails="date: published 2023"),
    "W3015993909": M("off_scope", "review"),
    "W3022811568": M("off_scope", "dosing commentary"),
    "W3090900933": M("off_scope", "bioinformatics study"),
    "W3120192825": M("off_scope", "ecological commentary"),
    "W3151682046": M("off_scope", "mouse study"),
    "W3172450895": M("off_scope", "review"),
    "W3174079333": M("off_scope", "animal study"),
    "W3192232281": M("off_scope", "review"),
    "W3216772674": M("off_scope", "mechanism review"),
    "W4200555363": M("off_scope", "knowledge-attitude-practice survey"),
    "W4206984550": M("off_scope", "commentary"),
    "W4223565472": M("off_scope", "review"),
    "W4224217742": M("off_scope", "in vitro study"),
    "W4245877834": M("off_scope", "journal rapid response (letter)"),
    "W4281912386": M("off_scope", "commentary"),
    "W4289979425": M("off_scope", "commentary"),
    "W3036124991": M("off_scope", "commentary"),
    "W3083341424": M("off_scope", "hypothesis paper"),
    "W3086865863": M("off_scope", "review"),
    "W3092224401": M("off_scope", "rat study (nebulized ivermectin)"),
    "W3122293810": M("off_scope", "review"),
    "W4283214729": M("off_scope", "review"),
    "W4285008448": M("off_scope", "formulation (lab) study"),
    "W4311448150": M("off_scope", "letter to the editor about TOGETHER"),
    "W4317477351": M("off_scope", "commentary on a trial protocol"),
    "W4318041390": M("off_scope", "review"),
    "W4319953714": M("off_scope", "commentary on long COVID"),
    "W4323344321": M("off_scope", "editor's evaluation of another paper"),
    "W4324140832": M("off_scope", "observational study of atazanavir plus ivermectin"),
    "W4362452768": M("off_scope", "scoping review"),
    "W4379508426": M("off_scope", "case report (liver injury)"),
    "W4386686318": M("off_scope", "review"),
    "W4394929346": M("off_scope", "in vitro study"),
    "W4243260355": M("near_miss", "RCT, ivermectin alone vs HCQ plus ivermectin plus azithromycin",
                     fails="comparator: a combination that itself contains ivermectin"),
    # checked by hand: reviews, peer-review notes, letters, lab work, 2024 combination trials
    "W3081745349": M("off_scope", "guideline"),
    "W3117652431": M("off_scope", "network meta-analysis"),
    "W3123539721": M("off_scope", "systematic review"),
    "W3147285122": M("off_scope", "commentary on another trial"),
    "W3158596488": M("off_scope", "narrative review"),
    "W3166599105": M("off_scope", "systematic review"),
    "W3188550925": M("off_scope", "methods review of trial reporting"),
    "W3200289841": M("off_scope", "systematic review protocol"),
    "W3202911911": M("off_scope", "systematic review"),
    "W3203491338": M("off_scope", "systematic review"),
    "W4206186030": M("off_scope", "review"),
    "W4220763537": M("off_scope", "systematic review"),
    "W4220764004": M("off_scope", "review"),
    "W4285545929": M("off_scope", "meta-analysis"),
    "W4291378096": M("off_scope", "peer reviews of a preprint"),
    "W4291378099": M("off_scope", "peer review of a preprint"),
    "W4308623331": M("off_scope", "review update"),
    "W4309361513": M("off_scope", "systematic review (prophylaxis)"),
    "W4313209660": M("off_scope", "meta-analysis (prophylaxis)"),
    "W4322712069": M("off_scope", "meta-analysis"),
    "W4323320726": M("off_scope", "author response to peer review"),
    "W4323344350": M("off_scope", "decision letter"),
    "W4388229766": M("off_scope", "in vitro study"),
    "W4396553701": M("off_scope", "review (metformin)"),
    "W4405274303": M("off_scope", "systematic review"),
    "W3143180683": M("off_scope", "prophylaxis trial with iota-carrageenan"),
    "W4393198428": M("off_scope", "2024, ivermectin plus colchicine"),
    "W4406827333": M("off_scope", "2024, ivermectin plus colchicine"),
    "W4393320918": M("off_scope", "2024, combination therapy"),
    "W4396610082": M("off_scope", "2024, losartan plus ivermectin"),
    # neutral
    "W3033863786": M("neutral", "trial protocol (SAINT)"),
    "W3109673381": M("neutral", "trial protocol (IVERCOR)"),
    "W3118321049": M("neutral", "trial protocol"),
    "W3139118535": M("neutral", "trial protocol (SAINT-Peru)"),
    "W3168599965": M("neutral", "trial design paper"),
    "W4388052115": M("neutral", "trial design paper (ACTIV-6 operations)"),
    "W4316684939": M("neutral", "about epilepsy, not COVID-19 treatment"),
}

TITLE_RULES = [
    ("review or commentary", r"\b(systematic review|meta-analys|meta analys|review|overview|perspective|commentary|"
                             r"editorial|letter|viewpoint|guideline|evidence|should not|unacceptable|politicis|"
                             r"fraud|integrity|bias|pitfalls|magic|plausible|potential|update|current|role of|"
                             r"lessons|reposicionamento|spending|survey|keeping rigor|ready to be|reply|response|"
                             r"comment|correspondence|hype|debate|misinformation|controvers|why)"),
    ("lab or pharmacology study", r"\b(in vitro|in silico|docking|molecular|computational|cell|vero|hamster|mice|"
                                  r"murine|pharmacokinetic|pharmacodynamic|pharmacology|interactions|antiviral "
                                  r"properties|inhibit|binding|mechanism|nanoparticle|formulation)"),
    ("observational study or case report", r"\b(retrospective|cohort|observational|case series|case-control|"
                                           r"real-world|compassionate|registry|cross-sectional|associated with|"
                                           r"toxic|neurotoxicity|outbreak|program|poison|prescri|case report|adverse)"),
    ("combination or prophylaxis design", r"\b(combination|combined|with doxycycline|azithromycin|carrageenan|zinc|"
                                          r"versus|prophyla|prevent)"),
]


TRAP_LABELS = ("trap_retracted", "trap_superseded_preprint")
SPOT_CHECK_SEED = 2026
SPOT_CHECK_SIZE = 15


def about_ivermectin_covid(p: dict) -> bool:
    t = f"{p['title']} {p['abstract']}".lower()
    return "ivermectin" in t and re.search(r"covid|sars-cov-2|coronavirus", t) is not None


def first_title_rule(title: str):
    """Return (category, match) for the first TITLE_RULES pattern found in the title, or None."""
    for category, rx in TITLE_RULES:
        match = re.search(rx, title)
        if match:
            return category, match
    return None


def load_inputs() -> tuple[dict, dict]:
    """The frozen corpus (id -> paper) and the snapshot's resolved curated ids."""
    with open(CORPUS / "papers.jsonl") as f:
        papers = {p["id"]: p for p in map(json.loads, f)}
    res = json.loads((CORPUS / "resolved_ids.json").read_text())
    return papers, res


def assign_labels(papers: dict, res: dict) -> dict[str, dict]:
    """Label every paper. Earlier steps win: a paper keeps the first label it gets."""
    labels: dict[str, dict] = {}

    def put(pid, entry):
        if pid and pid in papers:
            labels[pid] = {**entry, "title": papers[pid]["title"][:120]}

    # 1. Curated groups from the snapshot.
    for name, pid in res["gold"].items():
        put(pid, M("gold", f"included by the review: {name}"))
    for name, pid in res["traps_retracted"].items():
        put(pid, M("trap_retracted", name))
    for group in ("crossref_preprints", "openalex_preprints"):
        for name, pid in res.get(group, {}).items():
            put(pid, M("trap_superseded_preprint", f"{name}; its journal version is gold"))
    for name, pid in res["near_miss"].items():
        label, fails = name.split(" | ", 1)
        put(pid, M("near_miss", label, fails=fails))
    for name, pid in res["other_curated"].items():
        lab, why, unsure = CURATED_OTHER.get(name, ("off_scope", name, False))
        put(pid, M(lab, why, unsure))

    # 2. Retraction notices, then hand-made labels for papers not curated above.
    for pid, p in papers.items():
        if p.get("notice_for"):
            put(pid, M("neutral", f"retraction notice for {p['notice_for']}"))
    for pid, entry in MANUAL.items():
        if pid not in labels:
            put(pid, entry)

    # 3. Everything else: topic check, then title rules.
    for pid, p in papers.items():
        if pid in labels:
            continue
        if not about_ivermectin_covid(p):
            put(pid, M("neutral", "not about ivermectin for COVID-19"))
            continue
        rule = first_title_rule(p["title"].lower())
        if rule:
            category, match = rule
            text = f"{p['title']} {p['abstract']}".lower()
            # A title rule on a paper that says it is randomized might be hiding an eligible trial.
            unsure = bool(re.search(r"randomi[sz]", text))
            put(pid, M("off_scope", f"{category} (title: '{match.group(0)}')", unsure))
        else:
            put(pid, M("UNLABELLED", "needs a manual decision", True))

    # 4. Every retracted or withdrawn paper is a trap, whatever else it is.
    for pid, p in papers.items():
        if p.get("status") == "retracted" and labels.get(pid, {}).get("label") != "trap_retracted":
            prev = labels.get(pid, {})
            put(pid, M("trap_retracted", f"retracted (found in the corpus); otherwise {prev.get('label')}: "
                                         f"{prev.get('why')}"))
            labels[pid]["was"] = prev.get("label")
    return labels


def collect_report_of(papers: dict, labels: dict) -> dict[str, str]:
    """Reports of the same trial: recall counts trials, not reports. Superseded preprints and
    conference abstracts point to the trial's main (gold or relevant) report."""
    report_of = {k: v["report_of"] for k, v in labels.items() if v.get("report_of")}
    for pid, p in papers.items():
        if p.get("published_version_id") and labels.get(pid, {}).get("label") == "trap_superseded_preprint":
            report_of[pid] = p["published_version_id"]
    return report_of


def ids_with_label(labels: dict, *wanted: str) -> list[str]:
    return sorted(k for k, v in labels.items() if v["label"] in wanted)


def build_output(labels: dict, res: dict, report_of: dict) -> dict:
    """The labels.json structure that write_case1_yaml.py and validate.py read."""
    return {
        "key_ids": [res["gold"][k] for k in KEY],
        "gold_ids": ids_with_label(labels, "gold"),
        "relevant_ids": ids_with_label(labels, "gold", "relevant"),
        "near_miss": [{"id": k, "fails": labels[k]["fails"]} for k in ids_with_label(labels, "near_miss")],
        "off_scope_ids": ids_with_label(labels, "off_scope", "near_miss"),
        "trap_ids": ids_with_label(labels, *TRAP_LABELS),
        "report_of": dict(sorted(report_of.items())),
        "unlabelled": [k for k, v in labels.items() if v["label"] == "UNLABELLED"],
        "unsure": sorted(k for k, v in labels.items() if v.get("unsure")),
        "papers": dict(sorted(labels.items())),
    }


def print_review(papers: dict, labels: dict, out: dict) -> None:
    """Print label counts, unlabelled and unsure papers, and a fixed-seed spot-check sample."""
    counts: dict[str, int] = {}
    for v in labels.values():
        counts[v["label"]] = counts.get(v["label"], 0) + 1
    print("counts:", counts)
    for k in out["unlabelled"]:
        print("UNLABELLED:", k, papers[k]["date"], papers[k]["title"][:110])

    def show(k: str) -> str:
        reason = (labels[k].get("fails") or labels[k]["why"])[:80]
        return f"  {k:14} {labels[k]['label']:10} {reason:80} | {papers[k]['date']} {papers[k]['title'][:70]}"

    print(f"\nUNSURE ({len(out['unsure'])}):")
    for k in out["unsure"]:
        print(show(k))
    pool = [k for k, v in labels.items() if v["label"] in ("relevant", "near_miss", "off_scope") and not v.get("unsure")]
    print(f"\nRANDOM {SPOT_CHECK_SIZE} FOR SPOT-CHECK (seed {SPOT_CHECK_SEED}, "
          "from relevant / near-miss / off-scope, excluding unsure):")
    for k in sorted(random.Random(SPOT_CHECK_SEED).sample(pool, SPOT_CHECK_SIZE)):
        print(show(k))


def main() -> None:
    papers, res = load_inputs()
    labels = assign_labels(papers, res)
    out = build_output(labels, res, collect_report_of(papers, labels))
    (CORPUS / "labels.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print_review(papers, labels, out)


if __name__ == "__main__":
    main()
