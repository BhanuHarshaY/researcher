"""Dev-time: label the case 2 corpus. Run after corpus_tools/snapshot.py.

  python3 cases/case2_related_work/build/label.py

Writes corpus/labels.json: every paper's label, a one-line reason, and an
`unsure` flag for decisions a second person should check. Prints the unsure
labels and a fixed-seed random sample of 15 for spot-checking. case.yaml's id
lists are written from labels.json by build/write_yaml.py.

Gold source: Castelo, Bos & Lehmann 2019 (J Marketing Research 56:809). Gold
is the subset of its references about relying on algorithms, statistical
models or computer decision aids versus human judgment (and the two
advice-taking papers it uses for the reliance paradigm). Its other references
(mind perception, dehumanization, e-commerce trust, diffusion models, news
articles) are not gold. The source paper itself is excluded from the corpus,
because its reference list is the answer key.

Labels:
- gold: the source's related-work references described above.
- relevant: gold plus other papers whose subject is how people weigh, trust,
  choose or rely on algorithms / statistical models / AI / computer decision
  aids versus human judgment or advice (algorithm aversion and appreciation,
  reactions to algorithmic vs human decisions), and general reviews of the
  clinical-versus-statistical prediction evidence (the debate's origins).
- off_scope: tempting neighbours a careful related-work section on this topic
  would not cite: algorithms or AI without a question about people relying on
  them (technical ML, fairness methods, recommender algorithms, diagnostic
  accuracy validations), algorithmic management of workers, ethics,
  governance and adoption essays on AI in medicine or education, robo-advisor
  industry pieces, and keyword look-alikes.
- neutral: ambiguous or adjacent work (trust in automation from human
  factors, advice taking with human advisors only, technology acceptance,
  fairness perceptions of algorithmic decisions, domain-specific
  clinical-vs-actuarial accuracy studies, non-English papers, OSF study
  records) and retraction notices. Neutral papers count against precision
  only.
- trap_retracted: retracted papers on the topic (each has its real notice).
- trap_superseded_preprint: SSRN working papers whose journal version is gold.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "corpus"

KEY = ["Dawes, Faust & Meehl 1989", "Dietvorst, Simmons & Massey 2015", "Logg, Minson & Moore 2019"]
PAIRS = [("Dietvorst, Simmons & Massey 2015", "Logg, Minson & Moore 2019"),       # primary: opposite findings
         ("Dietvorst, Simmons & Massey 2015", "Dietvorst, Simmons & Massey 2018"),  # secondary: same first author
         ("Dietvorst, Simmons & Massey 2015", "Dietvorst & Bharti 2020")]           # added in v2: third Dietvorst paper


def M(label, why, unsure=False):
    return {"label": label, "why": why, "unsure": unsure}


R, O, N = "relevant", "off_scope", "neutral"

GOLD_WHY = {  # what each gold paper contributes; all are references of Castelo et al. 2019
    "Dawes, Faust & Meehl 1989": ("origin of the debate: actuarial methods beat clinical judgment", False),
    "Dietvorst, Simmons & Massey 2015": ("algorithm aversion after seeing algorithms err", False),
    "Logg, Minson & Moore 2019": ("algorithm appreciation: people prefer algorithmic advice", False),
    "Dietvorst, Simmons & Massey 2018": ("people use imperfect algorithms if they can modify them", False),
    "Grove et al. 2000": ("meta-analysis: mechanical beats clinical prediction", False),
    "Longoni, Bonezzi & Morewedge 2019": ("resistance to medical AI", False),
    "Yeomans et al. 2019": ("recommender systems vs people for jokes; people prefer humans", False),
    "Onkal et al. 2009": ("advice from statistical methods discounted vs human experts", False),
    "Promberger & Baron 2006": ("patients trust physicians over computers", False),
    "Shaffer et al. 2013": ("physicians who use a diagnostic aid are derogated", False),
    "Eastwood, Snook & Luther 2012": ("lay preference for clinical over actuarial decision strategies", False),
    "Diab et al. 2011": ("lay perceptions of selection decision aids", False),
    "Blattberg & Hoch 1990": ("combining models with managerial intuition", False),
    "Komiak & Benbasat 2006": ("trust in recommendation agents; recommender trust is otherwise neutral", True),
    "Armstrong 1980": ("experts vs simple methods in forecasting", False),
    "Sniezek & Buckley 1995": ("judge-advisor paradigm used to measure reliance; title-only record", True),
    "Soll & Larrick 2009": ("how people weight advice (reliance paradigm); human-advisor advice taking is "
                            "otherwise neutral", True),
}

CURATED_OTHER = {  # label for papers in the snapshot's "other_curated" group
    "Dawes 1979 (improper linear models)": M(R, "origin of the debate: improper linear models beat expert judgment"),
    "Highhouse 2008 (reliance on intuition in selection)": M(R, "resistance to statistical decision aids in hiring"),
    "Dzindolet et al. 2003 (trust in automation reliance)": M(R, "reliance on an automated decision aid after seeing "
                                                               "it err (title-only record)", True),
    "Prahl & Van Swol 2017 (advice from automation)": M(R, "advice from automation discounted after errors"),
    "Bigman & Gray 2018 (machines making moral decisions)": M(R, "aversion to machines making moral decisions"),
    "Glikson & Woolley 2020 (review: trust in AI)": M(R, "review of empirical research on human trust in AI"),
    "Lee & See 2004 (trust in automation)": M(N, "trust in automation (human-factors literature); adjacent", True),
    "Kawaguchi 2021 (workers following an algorithm)": M(R, "field experiment: workers following an algorithm's "
                                                          "recommendations (title-only record)"),
    "Burton, Stein & Jensen 2020 (review)": M(R, "systematic review of algorithm aversion"),
    "Mahmud et al. 2022 (review)": M(R, "systematic review of algorithm aversion"),
    "Jussupow, Benbasat & Heinzl 2020 (review)": M(R, "literature review of algorithm aversion"),
    "Bogert, Schecter & Watson 2021": M(R, "reliance on algorithms vs social influence as tasks get harder"),
    "Dietvorst & Bharti 2020": M(R, "people reject algorithms in uncertain domains (diminishing sensitivity to "
                                    "error); added in v2 as a third Dietvorst paper; postdates the source, so not gold"),
    "Davis, Bagozzi & Warshaw 1989 (technology acceptance)": M(N, "technology acceptance in general, not algorithms "
                                                                "vs human judgment; cited by the source"),
    "Li, Hess & Valacich 2008 (trust in new technology)": M(N, "trust in new information systems in general; "
                                                             "cited by the source (title-only record)"),
}

DOMAIN = "applied clinical-vs-statistical accuracy comparison in one domain"
HUMAN_ADVICE = "advice taking with human advisors only"
AUTOMATION = "trust in automation (human-factors literature); adjacent"
ALGO_MGMT = "algorithmic management of platform workers"
FAIRNESS = "algorithmic fairness methods"
OSF = "OSF study record (preregistration or data), not a paper"

MANUAL = {
    "W1001721205": M(N, f"{DOMAIN} (youth treatment failure)"),
    "W1964596829": M(N, "memory and search engines; not about relying on algorithmic judgment"),
    "W1987352340": M(R, "essay on Meehl's clinical-vs-actuarial evidence and resistance to it (origins)", True),
    "W1987876819": M(N, "models content-sharing preferences; not about relying on algorithms"),
    "W2006758438": M(N, f"{DOMAIN} (jaundice diagnosis)"),
    "W2020239630": M(N, f"{DOMAIN} (violence prediction)"),
    "W2022480405": M(N, "statistics textbook"),
    "W2026514799": M(N, f"{DOMAIN} (MMPI diagnosis); a classic, but borderline"),
    "W2042281163": M(O, "recommender algorithm (technical); no question about people relying on it"),
    "W2060144485": M(N, AUTOMATION),
    "W2067533265": M(N, f"{DOMAIN} (dangerousness)"),
    "W207333959": M(R, "review of the clinical-vs-actuarial prediction evidence (origins)"),
    "W2075329139": M(R, "compares human and recommender-system predictions of people's tastes"),
    "W2082409438": M(N, f"{DOMAIN} (jaundice)"),
    "W2088194274": M(N, f"{DOMAIN} (pharyngitis)"),
    "W2093669100": M(O, "'algorithm' is a surgical treatment protocol; patient outcomes, not reliance on judgment"),
    "W2098593402": M(O, "recommender-algorithm stability (technical)"),
    "W2102256472": M(R, "Grove & Meehl 1996: classic review of the clinical-statistical controversy (origins)"),
    "W2108700941": M(O, "IBM Watson's game strategy; no question about people relying on it"),
    "W2110325612": M(O, "collaborative-filtering algorithms (technical)"),
    "W2115281393": M(N, "book on fast-and-frugal heuristics; background on judgment"),
    "W2122469309": M(O, "'actuarial' means survival statistics vs risk models; not human vs algorithmic judgment"),
    "W2129871510": M(R, "review of actuarial vs clinical prediction in psychopathology (origins)", True),
    "W2131472525": M(N, "training human forecasters; no algorithm comparison"),
    "W2142135351": M(N, AUTOMATION),
    "W2159071801": M(N, "fast-and-frugal heuristics; background on judgment"),
    "W2166605778": M(N, f"{DOMAIN} (review of violence prediction)"),
    "W2239750798": M(N, HUMAN_ADVICE),
    "W2330414371": M(N, "methods paper on rule-based prediction; not about people relying on algorithms"),
    "W2359880483": M(N, HUMAN_ADVICE),
    "W2372682446": M(N, HUMAN_ADVICE),
    "W2516558179": M(O, "recommender-system method (technical)"),
    "W2536062718": M(R, "Logg's dissertation on when people rely on algorithms (precursor of Logg et al. 2019)"),
    "W2551317447": M(R, "judges' decisions vs machine predictions: algorithms outperform human judgment"),
    "W2555250062": M(R, "reliance on a decision aid in personnel selection"),
    "W2557738935": M(O, "deep-learning diagnostic accuracy validation; no question about reliance"),
    "W2592141406": M(N, "user trust in movie recommender systems; borderline"),
    "W2667569599": M(N, f"{HUMAN_ADVICE} (anchoring)"),
    "W2684480053": M(O, FAIRNESS),
    "W2737666587": M(N, HUMAN_ADVICE),
    "W2754764889": M(R, "beliefs about algorithmic vs human work (authenticity)"),
    "W2757799378": M(N, AUTOMATION),
    "W2766939712": M(O, FAIRNESS),
    "W2778043699": M(O, "literary criticism ('an algorithmic appreciation' of a novelist), not algorithm appreciation"),
    "W2784472442": M(O, "trust-aware recommender algorithm (technical)"),
    "W2792183666": M(R, "perceptions of algorithmic vs human managerial decisions (fairness, trust)"),
    "W2806853752": M(N, "AI vs dermatologists' accuracy in one domain; no question about reliance"),
    "W2810722110": M(O, "legal essay on AI in banking"),
    "W2898983491": M(O, "conceptual overview of trust in healthcare AI; no evidence on reliance"),
    "W2909340128": M(N, "conceptual paper on human-AI trust and automation allocation"),
    "W2913832730": M(O, "industry overview of robo-advisors"),
    "W2949300685": M(N, f"{HUMAN_ADVICE} (advisor gender)"),
    "W2983137008": M(R, "users' assessments of an algorithm's accuracy"),
    "W2985126436": M(R, "use of advice from robo-advisors"),
    "W3007153134": M(O, ALGO_MGMT),
    "W3013872196": M(O, "philosophical essay on trust in medical AI"),
    "W3023069697": M(O, "ethics of algorithmic fairness in health care"),
    "W3029022080": M(N, "perceived fairness of algorithmic decisions; adjacent"),
    "W3034107461": M(N, "essay on robo-advisors vs human advisors; borderline"),
    "W3037983463": M(O, "commentary on trusting AI"),
    "W3041672775": M(O, "essay on AI and medical humanities"),
    "W3042034256": M(R, "algorithm appreciation across task difficulty"),
    "W3042817621": M(R, "systematic review of algorithm aversion and appreciation"),
    "W3046553882": M(R, "algorithm appreciation in creative tasks"),
    "W3081297476": M(R, "personality and trust in humans vs AI"),
    "W3086839219": M(N, "business angels vs machine learning returns; accuracy comparison in one domain"),
    "W3087513280": M(R, "robo-investment aversion: preference for human vs algorithmic fund managers"),
    "W3092998473": M(O, FAIRNESS),
    "W3094877022": M(N, "sociological essay on predictive algorithms replacing judgment"),
    "W3103422570": M(R, "algorithm appreciation: performance, development process, interaction"),
    "W3110817755": M(R, "algorithm aversion and an algorithm's demonstrated ability to learn"),
    "W3113060706": M(O, ALGO_MGMT),
    "W3120272807": M(R, "human judgment as input to prediction algorithms", True),
    "W3123555980": M(N, "explanations for algorithmic transparency (XAI); adjacent"),
    "W3127461705": M(N, "broad review of stakeholder trust in AI; borderline"),
    "W3128351871": M(R, "consumer responses to algorithm vs human errors"),
    "W3130446240": M(R, "survey of human judgment and quantitative forecasting methods", True),
    "W3144032957": M(O, "scale for awareness of algorithmic media curation, not reliance on algorithmic judgment"),
    "W3153711671": M(N, "German-language working paper on algorithm aversion; on topic, unlikely in an English "
                        "related-work section", True),
    "W3154760526": M(N, "German-language working paper on algorithm aversion; on topic, unlikely in an English "
                        "related-work section", True),
    "W3164041257": M(N, AUTOMATION),
    "W3167050492": M(R, "reactions to erring algorithms"),
    "W3170495160": M(O, "philosophical defence of trust in medical AI"),
    "W3172101419": M(O, "review of algorithmic systems in government (accountability, privacy)"),
    "W3175413073": M(O, "expert disagreement about deep learning"),
    "W3177900756": M(R, "consumer reactions to decisions by algorithms vs humans"),
    "W3178993634": M(O, "algorithmic management at work"),
    "W3181173654": M(R, "Dietvorst & Bartels: objections to algorithms making moral tradeoffs"),
    "W3189444386": M(R, "algorithm transparency and use of algorithmic advice"),
    "W3193926864": M(R, "lay beliefs about AI and adoption of algorithmic advice"),
    "W3199747482": M(R, "confidence in AI and acceptance of AI suggestions"),
    "W3201716397": M(R, "mitigating algorithm aversion in forecasting"),
    "W3205077746": M(N, "German-language working paper on algorithm aversion; on topic, unlikely in an English "
                        "related-work section", True),
    "W3206874785": M(R, "reconciling algorithm aversion and appreciation"),
    "W3210797883": M(R, "past algorithm performance and acceptance of algorithmic advice"),
    "W4200010586": M(R, "political conservatism and aversion to AI"),
    "W4206578055": M(N, f"{DOMAIN} (housing program exits)"),
    "W4206941179": M(R, "algorithm use over time"),
    "W4210390504": M(R, "preference for moral discretion over algorithms"),
    "W4211002924": M(R, "public officials' adherence to algorithmic advice"),
    "W4213426744": M(N, "perspective on transparency and trust in human-AI teams"),
    "W4220795885": M(R, "motivation model of algorithm aversion"),
    "W4220880629": M(N, "Korean-language study of patient compliance with medical AI; on topic, abstract not "
                        "in English", True),
    "W4220936192": M(N, "user trust in conversational recommender systems; borderline"),
    "W4221104095": M(R, "algorithm aversion and counter-normative decision procedures"),
    "W4223643457": M(O, "algorithmic bias and fairness overview"),
    "W4225105901": M(R, "terminology (computer program, algorithm, AI) and human perceptions"),
    "W4225986817": M(R, "perceptions of algorithmic vs human judges"),
    "W4229044793": M(R, "advice accuracy and trust in algorithmic advice"),
    "W4248125493": M(R, "consumers' over-reliance on algorithmic recommendations"),
    "W4281822284": M(R, "algorithmic vs human advice and performance information"),
    "W4283162852": M(R, "overcoming algorithm aversion by learning from mistakes"),
    "W4283367157": M(O, "bioethics essay on algorithmic advice in clinical care"),
    "W4283643667": M(R, "trust processes for human vs automated trustees"),
    "W4283823343": M(R, "overcoming algorithm aversion: task-procedure fit"),
    "W4284961114": M(O, ALGO_MGMT),
    "W4287092540": M(R, "trust in algorithmic advice for fake-news detection"),
    "W4288174961": M(R, "algorithm-based advice taking in clinical judgment"),
    "W4291014911": M(R, "algorithm aversion and robo-advisors"),
    "W4292356785": M(N, "meta-analysis of advice taking (mostly human advisors); borderline", True),
    "W4293090552": M(R, "preferences for algorithmic advice in a word-association task"),
    "W4294865113": M(R, "algorithm aversion and self-driving cars"),
    "W4294963575": M(N, "negative user feelings toward recommender systems; adjacent"),
    "W4296978576": M(N, "perceptions of justice in algorithmic decisions; adjacent"),
    "W4304172675": M(O, "investment preferences of robo-advisor clients"),
    "W4306913606": M(O, "essay on trust in medical AI"),
    "W4308730821": M(O, "needs assessment for AI in medical education"),
    "W4309634305": M(R, "algorithm aversion in delegated investing"),
    "W4310071238": M(N, "German-language dissertation that includes algorithm-aversion studies", True),
    "W4313046324": M(O, "essay on the credibility of medical AI (black box)"),
    "W4313589447": M(O, ALGO_MGMT),
    "W4315880904": M(O, "ethics and governance of medical AI"),
    "W4321440879": M(R, "algorithm aversion under varying decision gravity"),
    "W4360621268": M(R, "user control and implicit attitudes toward algorithms"),
    "W4362610119": M(O, "trust in AI in farming (adoption overview)"),
    "W4366547314": M(R, "overcoming algorithm aversion: process vs outcome control"),
    "W4366599035": M(R, "algorithm appreciation or aversion under uncertainty"),
    "W4377042687": M(R, "book chapter titled 'Algorithm Aversion': public approval of news algorithms", True),
    "W4377292562": M(R, "introducing algorithmic advice to service customers"),
    "W4377563917": M(N, "clinicians' views on trust in AI decision support (medical-law article); borderline"),
    "W4379470483": M(O, "review of AI in healthcare"),
    "W4383104799": M(R, "perceived corruption reduces algorithm aversion"),
    "W4384572189": M(O, "algorithmic fairness and bias overview"),
    "W4385223878": M(R, "social and moral dimensions of algorithm aversion"),
    "W4385299043": M(R, "review of task-specific acceptance of algorithmic advice"),
    "W4385416124": M(O, f"{FAIRNESS} (clinical ML)"),
    "W4386218671": M(R, "educators' use of algorithmic advice"),
    "W4386914147": M(R, "terminology and responses to system failures", True),
    "W4387306298": M(R, "algorithm aversion among ridesharing drivers"),
    "W4387639604": M(R, "cooperation and trust with algorithms vs humans in trust games"),
    "W4388792924": M(O, "normative trust criteria for health AI"),
    "W4389396390": M(R, "decision authority and the returns to algorithms (human overrides)", True),
    "W4390512254": M(R, "familiarity and algorithm appreciation"),
    "W4390916974": M(N, "perceived fairness of algorithmic recruiting; adjacent"),
    "W4390951142": M(R, "perceived opacity and algorithm aversion at work"),
    "W4391114267": M(R, "implicit associations and algorithm aversion"),
    "W4391749788": M(R, "algorithms in selection decisions are effective but unappreciated"),
    "W4391904381": M(R, "recovery from algorithm aversion over time"),
    "W4392293913": M(O, ALGO_MGMT),
    "W4393165031": M(N, "theory of perceived AI agency and trust"),
    "W4394619247": M(O, "scoping review of AI in career development"),
    "W4398139642": M(O, "teachers' trust in AI and digital competence (adoption)"),
    "W4399170818": M(N, "trust in AI management of workers; adjacent to algorithmic management"),
    "W4399491432": M(R, "trust in AI-supported decision-making"),
    "W4400106250": M(N, "trust and serendipity in recommender systems; borderline"),
    "W4400445208": M(R, "evaluative algorithmic advice (field experiment)"),
    "W4400803056": M(R, "integrative perspective on algorithm aversion and appreciation"),
    "W4401046213": M(O, "medical students' perceptions of AI in education"),
    "W4402037523": M(O, "essay on AI and dehumanized patient care"),
    "W4403205285": M(R, "dynamics of reliance on algorithmic advice"),
    "W4403540152": M(R, "algorithm aversion in inventory decisions"),
    "W4403688812": M(R, "algorithm aversion toward performance feedback"),
    "W4404139911": M(R, "psychological distance and algorithm aversion"),
    "W4404186735": M(O, "review of algorithmic media use and literacy"),
    "W4404528809": M(R, "scale development for algorithm aversion"),
    "W4404663548": M(R, "use of algorithmic advice and performance feedback"),
    "W4407069508": M(R, "anatomy of algorithm aversion"),
    "W4407074920": M(O, ALGO_MGMT),
    "W4407578358": M(O, "survey of trust in health systems' use of AI; not reliance on algorithmic judgment"),
    "W4407736993": M(O, "robo-advisors in mutual funds (industry)"),
    "W4408459829": M(O, "interviews on accepting AI in medical history taking (technology acceptance)"),
    "W4408794157": M(R, "advice weighting in human-algorithm collaboration"),
    "W4409676962": M(N, AUTOMATION),
    "W4410884925": M(O, "economics essay on algorithms"),
    "W4410889186": M(O, "algorithmic pricing"),
    "W4410890093": M(R, "reliance on algorithmic advice (incentives, framing)"),
    "W4411330565": M(O, "philosophy of trust and transparency in AI"),
    "W4411527458": M(R, "valuation of human- vs algorithm-created products"),
    "W4411703968": M(O, "robo-advisors and behavioural biases (finance)"),
    "W4412114008": M(N, f"{HUMAN_ADVICE} (judge-advisor learning)"),
    "W4412211189": M(R, "algorithm appreciation and aversion in XAI-augmented clinical decisions"),
    "W4412296614": M(O, ALGO_MGMT),
    "W4412451403": M(N, "Spanish-language thesis on algorithm aversion and appreciation", True),
    "W4412926753": M(O, ALGO_MGMT),
    "W4413292088": M(R, "model comparing trust in humans and robots", True),
    "W4413354175": M(O, "robo-advisors and investment behaviour (finance)"),
    "W4414200236": M(R, "algorithm aversion toward improving AI"),
    "W4414525838": M(R, "managerial advice taking from human vs algorithmic advisers"),
    "W4415120095": M(O, "robo-advisors and bias mitigation (finance)"),
    "W4415165026": M(O, "robo-advisors in behavioural finance"),
    "W4415545653": M(R, "algorithm aversion and appreciation in unstructured tasks"),
    "W4416410027": M(R, "trust in AI recommendations (classroom experiment)", True),
    "W7105648595": M(N, f"{HUMAN_ADVICE} (point vs interval advice)"),
    "W7110905761": M(N, "OSF study record with a one-line description, not a paper"),
    "W7111817753": M(R, "explanation type and algorithm appreciation in healthcare"),
    "W7112351145": M(N, "OSF project (materials and data) for a 2024 paper, not a paper"),
    "W7113586290": M(N, AUTOMATION),
    "W7117683374": M(N, OSF), "W7117691885": M(N, OSF), "W7117760103": M(N, OSF),
    "W7117779892": M(N, OSF), "W7117893969": M(N, OSF), "W7127637853": M(N, OSF),
    "W7127239690": M(R, "psychological biases in algorithm appreciation or aversion"),
    "W7146978132": M(R, "algorithm explainability and algorithm aversion"),
    "W7211931508": M(N, "OSF preregistration of a replication of Dietvorst et al. 2018 (same short title), "
                        "not a paper"),
}


def main() -> None:
    papers = {json.loads(l)["id"]: json.loads(l) for l in open(CORPUS / "papers.jsonl")}
    res = json.loads((CORPUS / "resolved_ids.json").read_text())
    labels: dict[str, dict] = {}

    def put(pid, entry):
        if pid and pid in papers:
            labels[pid] = {**entry, "title": papers[pid]["title"][:120]}

    for name, pid in res["gold"].items():
        why, unsure = GOLD_WHY[name]
        put(pid, M("gold", f"cited by Castelo et al. 2019: {name}, {why}", unsure))
    for name, pid in res["traps_retracted"].items():
        put(pid, M("trap_retracted", name))
    for name, pid in res.get("crossref_preprints", {}).items():
        put(pid, M("trap_superseded_preprint", f"{name}; its journal version is gold"))
    for name, pid in res["other_curated"].items():
        put(pid, CURATED_OTHER[name])
    for pid, p in papers.items():
        if p.get("notice_for"):
            put(pid, M(N, f"retraction notice for {p['notice_for']}"))
    for pid, entry in MANUAL.items():
        if pid not in labels:
            put(pid, entry)
    for pid in papers:
        if pid not in labels:
            put(pid, M("UNLABELLED", "needs a manual decision", True))
    # Every retracted paper is a trap, whatever else it is.
    for pid, p in papers.items():
        if p.get("status") == "retracted" and labels[pid]["label"] != "trap_retracted":
            labels[pid] = {**M("trap_retracted", f"retracted (found in the corpus); otherwise {labels[pid]['label']}: "
                                                  f"{labels[pid]['why']}"), "title": p["title"][:120]}

    # A superseded preprint is another report of its gold paper: recall counts papers, not reports.
    report_of = {pid: p["published_version_id"] for pid, p in papers.items()
                 if p.get("published_version_id") and labels[pid]["label"] == "trap_superseded_preprint"}
    stale = [k for k in MANUAL if k not in papers]
    by = lambda *ls: sorted(k for k, v in labels.items() if v["label"] in ls)
    out = {
        "key_ids": [res["gold"][k] for k in KEY],
        "pairs": [[{**res["gold"], **res["other_curated"]}[a], {**res["gold"], **res["other_curated"]}[b]]
                  for a, b in PAIRS],
        "gold_ids": by("gold"),
        "relevant_ids": by("gold", R),
        "off_scope_ids": by(O),
        "trap_ids": by("trap_retracted", "trap_superseded_preprint"),
        "report_of": dict(sorted(report_of.items())),
        "unlabelled": by("UNLABELLED"),
        "unsure": sorted(k for k, v in labels.items() if v.get("unsure")),
        "papers": dict(sorted(labels.items())),
    }
    (CORPUS / "labels.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")

    counts: dict[str, int] = {}
    for v in labels.values():
        counts[v["label"]] = counts.get(v["label"], 0) + 1
    print("counts:", dict(sorted(counts.items())), "| total", len(labels))
    if stale:
        print("MANUAL entries not in the corpus:", stale)
    for k in out["unlabelled"]:
        print("UNLABELLED:", k, papers[k]["year"], papers[k]["title"][:110])
    show = lambda k: (f"  {k[:24]:24} {labels[k]['label']:9} {labels[k]['why'][:78]:78} | "
                      f"{papers[k]['year']} {papers[k]['title'][:60]}")
    print(f"\nUNSURE ({len(out['unsure'])}):")
    for k in out["unsure"]:
        print(show(k))
    pool = [k for k, v in labels.items()
            if v["label"] in (R, O, N) and not v.get("unsure") and not papers[k].get("notice_for")]
    print("\nRANDOM 15 FOR SPOT-CHECK (seed 2026, from relevant / off-scope / neutral, excluding unsure):")
    for k in sorted(random.Random(2026).sample(pool, 15)):
        print(show(k))


if __name__ == "__main__":
    main()
