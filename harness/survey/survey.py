"""Human mode: post-run survey in the terminal -> survey.json, plus an empty
interview_notes.md template. Questions mirror shared/survey_interview.md (a
unit test keeps the two in sync).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RULE = "─" * 72

# (key, label, question, low anchor, high anchor)
NASA_TLX = [
    ("mental_demand", "Mental demand", "How mentally demanding was the task?", "Very low", "Very high"),
    ("temporal_demand", "Temporal demand", "How hurried or rushed was the pace of the task?", "Very low", "Very high"),
    ("performance", "Performance", "How successful were you in accomplishing what you were asked to do?",
     "Perfect", "Failure"),
    ("effort", "Effort", "How hard did you have to work to accomplish your level of performance?",
     "Very low", "Very high"),
    ("frustration", "Frustration", "How insecure, discouraged, irritated, stressed, and annoyed were you?",
     "Very low", "Very high"),
]

# (item number, construct, statement, reverse_coded)
LIKERT = [
    (1, "controllability", "I could steer which papers the agent included.", False),
    (2, "controllability", "I could change my criteria without losing the work already done.", False),
    (3, "controllability", "I understood why papers were included or left out.", False),
    (4, "controllability", "I could check where each claim in the report came from.", False),
    (5, "trust", "I trust the paper set the agent produced.", False),
    (6, "over_reliance", "I would cite this report's claims without checking them myself.", True),
    (7, "trust", "I would be comfortable defending this review to my advisor or a reviewer.", False),
    (8, "engagement", "I stayed actively involved in the review rather than just reading the output.", False),
]
LIKERT_MIN, LIKERT_MAX = 1, 7

INTERVIEW = [
    "Walk me through a moment where you felt least in control. What would you have wanted to do?",
    "Was there a paper you expected to see? How did you find out whether it was included?",
    "When you asked the agent to change course, did the result match what you meant?",
    "How would you check this report before using it in your own paper?",
    "What one change would make you trust this tool more?",
]


class _EOF(Exception):
    pass


def _ask_int(prompt: str, lo: int, hi: int, inp, out) -> int | None:
    """Ask until a valid integer in [lo, hi] or 's' (skip -> None). EOF stops the survey."""
    while True:
        print(prompt, end=" ", file=out, flush=True)
        line = inp.readline()
        if line == "":
            raise _EOF
        s = line.strip().lower()
        if s in ("s", "skip"):
            return None
        try:
            v = int(s)
            if lo <= v <= hi:
                return v
        except ValueError:
            pass
        print(f"  Please enter a whole number from {lo} to {hi}, or s to skip.", file=out, flush=True)


def _mean(vals: list) -> float | None:
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def score_survey(tlx: dict, likert: dict[int, int | None]) -> dict:
    item6 = likert.get(6)
    return {
        "raw_tlx": _mean(list(tlx.values())),
        "controllability": _mean([likert.get(i) for i in (1, 2, 3, 4)]),
        "trust": _mean([likert.get(i) for i in (5, 7)]),
        "over_reliance": item6,
        "item6_reversed": None if item6 is None else LIKERT_MAX + LIKERT_MIN - item6,
        "engagement": likert.get(8),
    }


def run_survey(run_dir: str | Path, inp=None, out=None) -> dict:
    inp, out = inp or sys.stdin, out or sys.stdout
    tlx: dict[str, int | None] = {k: None for k, *_ in NASA_TLX}
    likert: dict[int, int | None] = {n: None for n, *_ in LIKERT}
    participant_id, completed = None, False

    print(f"\n{RULE}\nPOST-SESSION SURVEY (about 3 minutes). Type s to skip any question.\n{RULE}",
          file=out, flush=True)
    try:
        print("Participant ID (as given by the study team):", end=" ", file=out, flush=True)
        line = inp.readline()
        if line == "":
            raise _EOF
        participant_id = line.strip() or None

        print("\nPart 1 of 2. Rate each from 0 to 100.", file=out, flush=True)
        for key, label, q, lo, hi in NASA_TLX:
            tlx[key] = _ask_int(f"\n{label}: {q}\n  (0 = {lo}, 100 = {hi}) >", 0, 100, inp, out)

        print("\nPart 2 of 2. How much do you agree? 1 = strongly disagree, 4 = neutral, "
              "7 = strongly agree.", file=out, flush=True)
        for n, _c, text, _r in LIKERT:
            likert[n] = _ask_int(f"\n{n}. {text}\n  (1-7) >", LIKERT_MIN, LIKERT_MAX, inp, out)
        completed = True
    except _EOF:
        print("\n[Input ended; remaining answers saved as null.]", file=out, flush=True)

    result = {
        "participant_id": participant_id,
        "completed": completed,
        "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nasa_tlx": tlx,
        "nasa_tlx_scale": "0-100; performance: 0 = perfect, 100 = failure; others: 0 = very low, 100 = very high",
        "likert": [
            {"item": n, "construct": c, "statement": text, "reverse_coded": r, "response": likert[n]}
            for n, c, text, r in LIKERT
        ],
        "likert_scale": "1 = strongly disagree, 4 = neutral, 7 = strongly agree",
        "scores": score_survey(tlx, likert),
    }
    with open(Path(run_dir) / "survey.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nThank you. Survey saved. The interviewer will now ask a few short questions.\n{RULE}",
          file=out, flush=True)
    return result


def write_interview_template(run_dir: str | Path, config: dict, participant_id: str | None = None) -> Path:
    run_dir = Path(run_dir)
    lines = [
        f"# Interview notes: {config.get('case')} / {config.get('agent')} / {run_dir.name}",
        "",
        f"- Participant ID: {participant_id or ''}",
        "- Interviewer:",
        "- Date:",
        "- Duration (min):",
        "",
        "Questions are from shared/survey_interview.md. Write notes under each question; quote the "
        "participant where possible.",
        "",
    ]
    for i, q in enumerate(INTERVIEW, 1):
        lines += [f"## {i}. {q}", "", "Notes:", "", ""]
    lines += ["## Other observations", "", ""]
    path = run_dir / "interview_notes.md"
    path.write_text("\n".join(lines))
    return path
