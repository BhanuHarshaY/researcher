"""Dev-time: label the case 3 corpus (gold / relevant / off-scope / neutral) and the
post-change set for the scripted criteria change ("people with dementia only").

  python3 -m corpus_tools.label_case3

Gold source: Mahmoudi Asl et al. 2022 (J Med Internet Res 24:e37434), a scoping
review of 33 studies in which a social robot was used with older adults. Its
selection criteria: a social robot physically used in an experimental or
clinical study with people aged 65 or over; not acute care; no conference
abstracts, case studies, dissertations, books or reviews; not only robot
design or development; not stakeholder opinions without interaction; not
telepresence robots with only video-call features.

Labels:
- gold: the review's 33 included studies (refs 11 and 16-47).
- relevant: other empirical studies in which a social robot was used with older
  adults (the review's criteria).
- off_scope: the adjacent cluster that shares keywords but is outside the field:
  rehabilitation, assistive or surgical robots, exoskeletons, telepresence-only
  robots, social robots for children or autism, smart homes without a robot.
- neutral: reviews, design or development papers, opinion studies without
  interaction, and anything else not about either cluster. They count against
  precision only.
- dementia: the papers that stay valid after turn 2 narrows the map to people
  with dementia (gold: the review's 16 dementia studies; relevant: studies whose
  participants are people with dementia).
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

CORPUS = Path("cases/case3_field_map/corpus")

# Gold refs the review lists as studies of people with dementia (Results, "Participants and Settings").
GOLD_DEMENTIA_REFS = {"ref11", "ref18", "ref23", "ref24", "ref27", "ref29", "ref30", "ref31", "ref32", "ref33",
                      "ref34", "ref35", "ref38", "ref39", "ref43", "ref44"}
# Key papers must stay valid after the turn-2 narrowing to dementia (v1 used Hobbit and Banks 2008,
# which a correct narrowing drops). Liang 2017 RCT, Moyle 2013 PARO, and the two most-cited
# dementia studies in the corpus: Libin 2004 robocat, Valentí 2015 advanced dementia.
KEY_REFS = ["ref33", "ref35", "ref34", "ref43"]


def M(label, why, unsure=False, dementia=False):
    return {"label": label, "why": why, "unsure": unsure, "dementia": dementia}


# Hand review of every non-gold paper the rules could not settle (16 Nov 2026).
MANUAL: dict[str, dict] = {
    "W1178530349": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W1967507142": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W1986000980": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2019161055": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2039822570": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2040979576": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W2043587319": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2043711811": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2065178260": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2080923542": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2102035712": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2104286239": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2112421347": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2148142846": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W297025115": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2159536297": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W2282485379": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2585556435": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2592905630": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W2689483015": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W2771925981": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W2778691880": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W2782359998": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2784295971": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2883046174": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2924547041": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2943699887": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2946005838": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2958364445": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2995685337": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W2997199906": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W3015009700": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W3015603533": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W3033476063": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W3042720668": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W3088196398": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W3092218325": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W3102212853": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W3137166629": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W3198896322": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W4243437205": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W4407738599": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W759765632": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W1505024467": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W2080233792": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W3111679151": M("relevant", "empirical study: social robot used with older adults (checked)", False, True),
    "W382502046": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W1982844896": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W2072387963": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W3001702224": M("relevant", "empirical study: social robot used with older adults (checked)", False, False),
    "W1883246670": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W1973340331": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2000986314": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2033159471": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2060479977": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W2080394568": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2300792968": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2322289952": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2790313491": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W2791822482": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W2793187533": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W2980174560": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W3034490183": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W3041860695": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W3089483243": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W3113108394": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W3147388967": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W4251569456": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W1978404823": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2024647503": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W2025048472": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2094053894": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W2130723705": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2172131195": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W2560709470": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W2731113721": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2766970278": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2803451925": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2948083338": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W3094103867": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2046365492": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2068857685": M("relevant", "older-adult robot study; design or population needs a check", True, True),
    "W2107521387": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2953482672": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W2553308560": M("relevant", "older-adult robot study; design or population needs a check", True, False),
    "W1967149046": M("neutral", "survey of willingness, no interaction", False),
    "W1973812759": M("neutral", "ethnographic study of nursing homes, no robot used", True),
    "W2003566851": M("neutral", "single case study", True),
    "W2037270833": M("neutral", "ethnographic study, no robot used", False),
    "W2045063968": M("neutral", "overview", True),
    "W2047271476": M("neutral", "design paper", False),
    "W2049800038": M("neutral", "overview", False),
    "W2068000469": M("neutral", "survey without interaction", False),
    "W2120142058": M("neutral", "opinions without interaction", True),
    "W2133071626": M("neutral", "survey to inform design", False),
    "W2467392379": M("neutral", "sociological analysis of PARO", True),
    "W2550865791": M("neutral", "stakeholder opinions", False),
    "W2615550593": M("neutral", "conference abstract", False),
    "W2760294871": M("neutral", "design paper", False),
    "W2761596890": M("neutral", "therapists' opinions", False),
    "W2889731820": M("neutral", "conference abstract", False),
    "W2893222310": M("neutral", "survey without interaction", False),
    "W2895915058": M("neutral", "conference abstract", False),
    "W2896071495": M("neutral", "conference abstract", False),
    "W2899915867": M("neutral", "conference abstract", False),
    "W2982896790": M("neutral", "conference abstract", False),
    "W3036971864": M("neutral", "design paper (dialogue modelling)", False),
    "W3081435517": M("neutral", "hygiene of robots, not use with people", False),
    "W3093665998": M("neutral", "service robots, not with older adults", True),
    "W3097289914": M("neutral", "conference abstract", False),
    "W3110858436": M("neutral", "concept paper", False),
    "W3124540728": M("neutral", "engagement factors, population unclear", True),
    "W1561893471": M("neutral", "conference proceedings", False),
    "W1747498325": M("neutral", "book chapter", False),
    "W1899217968": M("neutral", "robot grasping, not older adults", False),
    "W2016497637": M("neutral", "essay", False),
    "W2036445299": M("neutral", "ethics essay", False),
    "W2049072188": M("neutral", "survey of preferences", False),
    "W2060981264": M("neutral", "robots in public, not older adults", False),
    "W2061309618": M("neutral", "museum robots", False),
    "W2151645026": M("neutral", "online forum analysis", False),
    "W2186444104": M("neutral", "ethics essay", False),
    "W2255700634": M("neutral", "questionnaire on PARO, general public", False),
    "W2614174016": M("neutral", "N=1 studies in mental health care, population unclear", True),
    "W2755397109": M("neutral", "review", False),
    "W2892152415": M("neutral", "essay", False),
    "W2946313803": M("neutral", "in-patient (acute) care, excluded setting", True),
    "W2963704405": M("neutral", "needs study, no robot used", False),
    "W2985997560": M("neutral", "essay", False),
    "W3001674704": M("neutral", "textbook", False),
    "W3002535960": M("neutral", "reflection paper", False),
    "W3094898599": M("neutral", "empathy in care robots, opinion study", True),
    "W3126403216": M("neutral", "philosophy paper", False),
    "W380842714": M("neutral", "review of PARO research", False),
    "W4253064634": M("neutral", "review", False),
    "W791115014": M("neutral", "social robots at home, not older adults", False),
    "W2024895316": M("neutral", "overview covering children and older adults", False),
    "W2963921568": M("neutral", "overview covering children and older adults", False),
    "W3008512828": M("neutral", "overview covering older adults and autism", False),
    "W2484033910": M("neutral", "perceptions without real use", True),
    "W2948448861": M("neutral", "attitude study, robot use unclear", True),
    "W2976777638": M("neutral", "user-centred design paper", True),
    "W3105249390": M("neutral", "stakeholder perceptions", True),
    "W2992521171": M("neutral", "attitude survey", True),
    "W3081595027": M("off_scope", "medication-dispensing device, not a social robot", True),
    "W2060018350": M("off_scope", "remote-communication avatar robot (telepresence-like)", True),
    "W2470287269": M("off_scope", "PARO with healthy young adults, not older adults", True),
    "W2913301016": M("off_scope", "telemedicine robot", True),
    "W2127217719": M("off_scope", "smart-home technologies overview (adjacent cluster)", False),
}

# Resolution of the unsure labels (16 Nov 2026), following Mahmoudi Asl 2022's criteria:
# relevant = empirical study in which older adults used or interacted with a social robot;
# dementia only if participants are described as living with dementia; design, overview,
# commentary, concept and system papers -> neutral; undecidable -> neutral; no robot -> off-scope.
RESOLVED = {
    "W1994379356": M("relevant", "Matilda deployed in homes of people with dementia for six months", False, True),
    "W4251569456": M("relevant", "robot walking-group assistant used with older adults with advanced dementia", False, True),
    "W3034490183": M("relevant", "robot cats used at home by people with dementia (qualitative study)", False, True),
    "W2521240520": M("relevant", "older adults with Alzheimer's prompted by a robot through daily activities", False, True),
    "W3105249390": M("relevant", "MARIO used with older people living with dementia (qualitative study)", False, True),
    "W1883246670": M("relevant", "RCT: nursing-home residents visited by a dog, PARO or a toy cat", False, False),
    "W3113108394": M("relevant", "pilot in two LTC sites: residents (10 MCI, 1 AD) engaged with a robot; the review counts cognitive impairment with dementia (ref11)", False, True),
    "W2003566851": M("relevant", "HRI study: residents played a memory game with Brian 2.1", False, False),
    "W2948448861": M("relevant", "older adults interacted with an assistive robot (attitudes before/after)", False, False),
    "W2976777638": M("relevant", "older people interacted with eight companion robots, then focus groups", False, False),
    "W2033159471": M("relevant", "experimental study: elderly participants exercised with a robot coach", False, False),
    "W2025048472": M("relevant", "proof-of-concept testing of a trainer robot with older adults", False, False),
    "W1973340331": M("relevant", "older adults used a robotic interface for photo albums", False, False),
    "W2046365492": M("relevant", "acceptance study: older adults interacted with Brian 2.1", False, False),
    "W2107521387": M("relevant", "30 older adults interacted with PARO", False, False),
    "W2731113721": M("relevant", "feasibility study: humanoid robot guided elderly people while walking", False, False),
    "W2766970278": M("relevant", "16 older adults partner-danced with a robot", False, False),
    "W2953482672": M("relevant", "PARO placed in homes of 10 older adults with depression for a month", False, False),
    "W2980174560": M("relevant", "23 older participants exercised with a robot coach", False, False),
    "W3089483243": M("relevant", "32 older adults exercised with Nao or Poppy coaches", False, False),
    "W2322289952": M("relevant", "humanoid robot tested with residents in three nursing homes", False, False),
    "W2113951489": M("neutral", "interface design study", False, False),
    "W1988401879": M("neutral", "requirements and design paper", False, False),
    "W1575107006": M("neutral", "attitudes without robot use", False, False),
    "W2774827160": M("neutral", "project abstract, nothing to decide from", False, False),
    "W2899969406": M("neutral", "design and system validation", False, False),
    "W2900350517": M("neutral", "conference abstract", False, False),
    "W2931420217": M("neutral", "design research with caregivers", False, False),
    "W3042224163": M("neutral", "survey of ethical perceptions", False, False),
    "W2172131195": M("neutral", "project progress overview", False, False),
    "W2060479977": M("neutral", "overview", False, False),
    "W2024647503": M("neutral", "system paper", False, False),
    "W2068857685": M("neutral", "focus groups and interviews, no robot use described", False, False),
    "W2094053894": M("neutral", "demo paper", False, False),
    "W2560709470": M("neutral", "system paper", False, False),
    "W2790313491": M("neutral", "system paper", False, False),
    "W2791822482": M("neutral", "symposium summary", False, False),
    "W2793187533": M("neutral", "system paper", False, False),
    "W3041860695": M("neutral", "letter to the editor; the record does not show robot use", False, False),
    "W3147388967": M("neutral", "doctoral thesis", False, False),
    "W1987900808": M("neutral", "attitude measurement, not older adults", False, False),
    "W968184718": M("neutral", "design paper", False, False),
    "W2068679643": M("neutral", "manual development, preliminary use with one caregiver and two patients", False, False),
    "W1948807083": M("neutral", "attitude survey and focus groups, no robot use", False, False),
    "W2467392379": M("neutral", "sociological analysis", False, False),
    "W2045063968": M("neutral", "systematic review", False, False),
    "W2113295453": M("neutral", "design guidelines", False, False),
    "W2120142058": M("neutral", "field study for robot design, no robot used", False, False),
    "W105479526": M("neutral", "ethics framework", False, False),
    "W1973812759": M("neutral", "field study for robot design, no robot used", False, False),
    "W2109135966": M("neutral", "conceptual framework", False, False),
    "W2227803205": M("neutral", "framework from focus groups", False, False),
    "W2484033910": M("neutral", "perceptions without robot use", False, False),
    "W2602852930": M("neutral", "thesis: behaviour development", False, False),
    "W7220496817": M("neutral", "ethics framework", False, False),
    "W2540268778": M("neutral", "thesis: robot development", False, False),
    "W2594575328": M("neutral", "participatory design", False, False),
    "W2734517545": M("neutral", "survey development", False, False),
    "W2772256242": M("neutral", "questionnaire study", False, False),
    "W2794445509": M("neutral", "perceptions study, no robot use described", False, False),
    "W2802487094": M("neutral", "healthcare providers, not older adults", False, False),
    "W2896242380": M("neutral", "system framework", False, False),
    "W2946313803": M("neutral", "literature, interviews and survey of directors", False, False),
    "W2947353480": M("neutral", "focus groups on ethics", False, False),
    "W2972564100": M("neutral", "interviews with professionals", False, False),
    "W2992521171": M("neutral", "attitude survey", False, False),
    "W3124540728": M("neutral", "thesis", False, False),
    "W3093570108": M("neutral", "panel saw a demonstration only", False, False),
    "W3093665998": M("neutral", "methods paper on field-study challenges", False, False),
    "W3094898599": M("neutral", "concept paper", False, False),
    "W2000986314": M("neutral", "older adults observed a robot demonstration only", False, False),
    "W1978404823": M("neutral", "system architecture paper", False, False),
    "W2080394568": M("neutral", "system development paper", False, False),
    "W2300792968": M("neutral", "methods paper", False, False),
    "W2130723705": M("neutral", "demo paper", False, False),
    "W2553308560": M("neutral", "essay", False, False),
    "W2803451925": M("neutral", "learning framework, user simulation", False, False),
    "W2948083338": M("neutral", "system paper", False, False),
    "W3094103867": M("neutral", "conference index entry, nothing to decide from", False, False),
    "W2614174016": M("off_scope", "PARO with adults with intellectual disability, not older adults", False, False),
    "W2112759888": M("off_scope", "smart home without a robot", False, False),
    "W2139886304": M("off_scope", "smart home without a robot", False, False),
    "W2035934412": M("off_scope", "sensor network without a robot", False, False),
    "W1488087939": M("off_scope", "smart home without a robot", False, False),
    "W2034181225": M("off_scope", "smart home without a robot", False, False),
    "W2102699948": M("off_scope", "fall detection without a robot", False, False),
    "W1517879342": M("off_scope", "smart home without a robot", False, False),
    "W2765275233": M("off_scope", "smart home review, no robot", False, False),
    "W2884360641": M("off_scope", "smart home sensors, no robot", False, False),
    "W2060018350": M("off_scope", "telepresence robot development", False, False),
    "W2470287269": M("off_scope", "PARO with healthy young adults, not older adults", False, False),
    "W2772424378": M("off_scope", "robotic device (hip exoskeleton), not a social robot", False, False),
    "W3003995186": M("off_scope", "robotic device (exoskeletons), not a social robot", False, False),
    "W3012841673": M("off_scope", "robotic device (exoskeleton review), not a social robot", False, False),
    "W2913301016": M("off_scope", "telepresence robot", False, False),
    "W3081595027": M("off_scope", "robotic medication dispenser, not a social robot", False, False),
}

OFF_RULES = [
    ("social robots for children or autism", r"\b(autis|asd\b|child|children|pediatric|paediatric|adolescen|kindergarten|school)"),
    ("rehabilitation, assistive or surgical robot", r"\b(exoskeleton|rehabilitat|gait|upper[- ]limb|lower[- ]limb|stroke|wheelchair|"
                                                    r"walker|walking aid|prosthe|surg|feeding robot|robotic arm|manipulator|"
                                                    r"lifting|transfer robot|physiotherap)"),
    ("telepresence robot", r"\b(telepresence|tele-presence|video call|videoconferenc|remote presence)"),
    ("smart home or sensing without a robot", r"\b(smart home|ambient assisted|sensor network|activity recognition|fall detection|"
                                               r"wearable)"),
]
NEUTRAL_RULES = [
    ("review", r"\b(review|survey of|overview|state of the art|meta-analys|systematic|scoping|literature)"),
    ("design or development paper", r"\b(architecture|framework|design|development|prototype|algorithm|navigation|"
                                    r"control system|ontology|model for|software|platform)"),
    ("opinions without interaction", r"\b(attitude|perception|opinion|expectation|focus group|views of|stakeholder)"),
]
# Robotic devices that are often described without the word "robot".
DEVICE_RE = r"\b(exoskeleton|exosuit|orthosis|wearable (walking )?assist|walking assist|soft[- ]robotic|power(ed)? assist)"
POP_RE = r"\b(older|elder|aged|ageing|aging|senior|dementia|alzheimer|nursing home|care home|aged care|residents|geriatric|65)"
STUDY_RE = r"\b(stud(y|ies)|trial|pilot|evaluat|intervention|participants|field test|experiment|session|effect)"
DEMENTIA_RE = r"\b(dementia|alzheimer|cognitive impairment|cognitively impaired)"


def main() -> None:
    papers = {json.loads(l)["id"]: json.loads(l) for l in open(CORPUS / "papers.jsonl")}
    res = json.loads((CORPUS / "resolved_ids.json").read_text())
    labels: dict[str, dict] = {}

    def put(pid, entry):
        if pid in papers:
            labels[pid] = {**entry, "title": papers[pid]["title"][:120]}

    gold_by_ref = {}
    for name, pid in res["gold"].items():
        ref = name.split()[0]
        gold_by_ref[ref] = pid
        put(pid, M("gold", f"included by the review: {name}", dementia=ref in GOLD_DEMENTIA_REFS))
    for pid, p in papers.items():
        if p.get("notice_for"):
            put(pid, M("neutral", f"retraction notice for {p['notice_for']}"))
    for pid, entry in {**MANUAL, **RESOLVED}.items():
        if pid not in labels:
            put(pid, entry)

    for pid, p in papers.items():
        if pid in labels:
            continue
        title = p["title"].lower()
        text = f"{p['title']} {p['abstract']}".lower()
        dem = bool(re.search(DEMENTIA_RE, text))
        if "robot" not in text:
            if re.search(DEVICE_RE, text):
                put(pid, M("off_scope", "robotic device (exoskeleton or assistive device), not a social robot"))
            elif re.search(OFF_RULES[3][1], text):
                put(pid, M("off_scope", "smart home or sensing without a robot"))
            else:
                put(pid, M("off_scope", "no robot involved"))
            continue
        off = next((c for c, rx in OFF_RULES if re.search(rx, title)), None)
        if off:
            put(pid, M("off_scope", f"{off} (title)", False))
            continue
        neu = next((c for c, rx in NEUTRAL_RULES if re.search(rx, title)), None)
        if neu:
            put(pid, M("neutral", f"{neu} (title)", neu != "review", dementia=dem))
            continue
        off_text = next((c for c, rx in OFF_RULES if re.search(rx, text)), None)
        if re.search(POP_RE, text) and re.search(STUDY_RE, text):
            # Study of a robot with older people: relevant, unless the abstract points to the adjacent cluster.
            if off_text:
                put(pid, M("UNLABELLED", f"older-adult robot study, but abstract mentions: {off_text}", True, dem))
            else:
                put(pid, M("relevant", "empirical study of a social robot with older adults", True, dem))
        else:
            put(pid, M("UNLABELLED", "robot paper without a clear older-adult study", True, dem))

    unlabelled = [k for k, v in labels.items() if v["label"] == "UNLABELLED"]
    by = lambda *ls: sorted(k for k, v in labels.items() if v["label"] in ls)
    post_change = sorted(k for k, v in labels.items() if v["label"] in ("gold", "relevant") and v.get("dementia"))
    out = {
        "key_ids": [gold_by_ref[r] for r in KEY_REFS],
        "gold_ids": by("gold"),
        "relevant_ids": by("gold", "relevant"),
        "off_scope_ids": by("off_scope"),
        "post_change_expected_ids": post_change,
        "unlabelled": unlabelled,
        "unsure": sorted(k for k, v in labels.items() if v.get("unsure")),
        "papers": dict(sorted(labels.items())),
    }
    (CORPUS / "labels.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    counts: dict[str, int] = {}
    for v in labels.values():
        counts[v["label"]] = counts.get(v["label"], 0) + 1
    print("counts:", counts, "| post-change (dementia) gold+relevant:", len(post_change),
          "of which gold:", sum(labels[k]["label"] == "gold" for k in post_change))
    show = lambda k: (f"  {k:12} {labels[k]['label']:10} {'D' if labels[k].get('dementia') else ' '} "
                      f"{labels[k]['why'][:55]:55} | {papers[k]['year']} {papers[k]['title'][:80]}")
    print(f"\nUNLABELLED ({len(unlabelled)}):")
    for k in unlabelled:
        print(show(k))
    print(f"\nUNSURE ({len(out['unsure'])}):")
    for k in out["unsure"]:
        if labels[k]["label"] != "UNLABELLED":
            print(show(k))
    pool = [k for k, v in labels.items() if v["label"] in ("relevant", "off_scope") and not v.get("unsure")]
    print("\nRANDOM 15 FOR SPOT-CHECK (seed 2026, relevant / off-scope, excluding unsure):")
    for k in sorted(random.Random(2026).sample(pool, min(15, len(pool)))):
        print(show(k))


if __name__ == "__main__":
    main()
