"""score_run end to end on the toy case with a fake judge, plus Judge request/parse checks."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

from harness.config import CASES_DIR
from harness.metrics.judge import (CLAIMS_SCHEMA, EXCLUSION_EXTRACT_SCHEMA, EXCLUSION_GROUNDING_SCHEMA,
                                   EXCLUSION_SCHEMA, REVIEW_STATE_SCHEMA, Judge, JudgeError)
from harness.metrics.score import cost_from_events, score_run

TOY = CASES_DIR / "_toy"
T004_TITLE = "The testing effect in undergraduate engineering statics: a randomized classroom experiment"


def ev(type_, turn=None, **kw):
    return {"type": type_, "ts": f"2026-11-16T10:00:{len(kw):02d}+00:00", "turn": turn, **kw}


TRAJECTORY = [
    ev("user_message", 1, source="sim", text="Review please."),
    ev("tool_call", 1, name="search_papers", input={"query": "retrieval"}, tool_use_id="tu1"),
    ev("tool_result", 1, tool_use_id="tu1", is_error=False, content="...", paper_ids=["T001", "T002", "T006"]),
    ev("usage", 1, role="agent", model="m", stop_reason="end_turn", input_tokens=10,
       cache_read_input_tokens=5, cache_creation_input_tokens=1, output_tokens=7),
    ev("agent_message", 1, text=(
        "| T001 | Intro biology RCT, n = 412 | Quiz group scored 8.4 points higher on the final |\n"
        "| T002 | Physics crossover design | Quizzed topics retained better on the delayed test |\n"
        "The preprint T006 reported an 11.2 point gain on the final exam in one section.\n"
        "Excluded: T009 because it is a middle school study and outside the population.")),
    ev("user_message", 2, source="sim", text=f'Why didn\'t you include "{T004_TITLE}"?'),
    ev("agent_message", 2, text="It does not exist in the database, so I could not include it."),
    ev("run_end", None, ok=True),
]


class FakeJudge:
    model = "fake-judge"

    def __init__(self):
        self.usage = []
        self.calls = []

    def review_state(self, transcript, candidates):
        self.calls.append(("review_state", [c["id"] for c in candidates]))
        roles = {"T001": "included", "T002": "included", "T006": "included", "T009": "excluded"}
        papers = [{"id": c["id"], "role": roles.get(c["id"], "mentioned"), "status_flagged": False,
                   "evidence": "x"} for c in candidates] + [{"id": "HALLUCINATED", "role": "included",
                                                              "status_flagged": False, "evidence": ""}]
        return {"papers": papers, "completeness_caveat": False, "caveat_quote": ""}

    def claims(self, units, papers, note=None):
        self.calls.append(("claims", [u["cited_ids"] for u in units], [p["id"] for p in papers]))
        labels = ["supported", "supported", "misattributed", "supported"]
        # A misattribution names another paper the judge was shown (a valid correct_id).
        other = lambda u: next(p["id"] for p in papers if p["id"] not in u["cited_ids"])
        return [{"index": i, "label": labels[i - 1],
                 "correct_id": other(units[i - 1]) if labels[i - 1] == "misattributed" else "", "rationale": "r"}
                for i in range(1, len(units) + 1)]

    def exclusion(self, criteria, title, seen_level, seen_text, facts, question, answer):
        self.calls.append(("exclusion", title, facts, seen_level))
        return {"reason_type": "process", "criterion_claims_grounded": True, "process_claims_accurate": False,
                "basis_disclosed": True, "rationale": "claims the paper is absent"}

    def exclusion_list_extract(self, seen_titles, question, answer):
        self.calls.append(("extract", [s["id"] for s in seen_titles]))
        return [{"id": "T009", "reason": "K-12", "basis_stated": "full_record", "basis_disclosed": True},
                {"id": "T010", "reason": "medical residents", "basis_stated": "snippet_or_abstract", "basis_disclosed": True},
                {"id": "T008", "reason": "meta-analysis", "basis_stated": "not_stated", "basis_disclosed": False},
                {"id": "T001", "reason": "re-reading control", "basis_stated": "not_stated", "basis_disclosed": False}]

    def exclusion_grounding(self, items):
        self.calls.append(("grounding", [(it["id"], it["seen_level"]) for it in items]))
        return [{"index": i, "grounded": True, "rationale": "r"} for i in range(1, len(items) + 1)]


class TestScoreRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name)
        (self.run / "config.json").write_text(json.dumps({"case": "_toy"}))
        (self.run / "trajectory.json").write_text(json.dumps(TRAJECTORY))

    def tearDown(self):
        self.tmp.cleanup()

    def test_toy_run_scores(self):
        judge = FakeJudge()
        reward, j = score_run(self.run, judge=judge, case_dir=TOY)
        self.assertEqual(reward["recall_gold"], 0.5)                     # T001, T002 of 4 gold
        self.assertEqual(reward["precision_set"], round(2 / 3, 4))       # T006 is not relevant
        self.assertEqual(reward["off_scope_rate"], 0.0)                  # T009 was excluded
        self.assertEqual(reward["bd_scope_drift"], 0)
        self.assertEqual(reward["trap_flag_rate"], 0.5)                  # T006 cited unflagged, T007 absent
        self.assertEqual(reward["bd_status_ignored"], 1)
        self.assertEqual(reward["bd_missed_key_paper"], 1)               # T004 missing
        self.assertEqual(reward["claim_support_rate"], 0.75)
        self.assertEqual(reward["bd_misattribution"], 1)
        self.assertEqual(reward["exclusion_explained"], 0)              # false claim about the database
        self.assertEqual(reward["bd_opaque_screening"], 1)
        self.assertIsNone(reward["near_miss_exclusion_rate"])            # toy has no near_miss_ids
        self.assertIsNone(reward["steer_preservation"])                  # toy has no criteria change
        self.assertIsNone(reward["bd_cant_steer"])
        self.assertEqual(reward["user_turns"], 2)                        # cost from events (no reward.json)
        self.assertEqual(reward["input_tokens"], 16)
        self.assertEqual(j["included_ids"], ["T001", "T002", "T006"])    # hallucinated id dropped
        self.assertEqual(j["errors"], [])

        # Exclusion facts come from the run log and the corpus graph.
        _, title, facts, seen_level = next(c for c in judge.calls if c[0] == "exclusion")
        self.assertTrue(title.startswith("The testing effect in undergraduate engineering statics"))
        self.assertEqual(seen_level, "never seen")
        text = " ".join(facts)
        self.assertIn("Keyword search cannot find it", text)
        self.assertIn("never appeared", text)
        self.assertIn("T001", text)                                      # cites T004, so a route to it
        # Claim judge sees cited papers plus similar papers.
        _, cited, shown = next(c for c in judge.calls if c[0] == "claims")
        self.assertIn(["T006"], cited)
        self.assertTrue({"T001", "T002", "T006"} <= set(shown))
        self.assertGreater(len(shown), 3)

    def test_recorded_followup_target_wins(self):
        # The sim user asked about T005 (picked at run time), not the case.yaml paper.
        traj = TRAJECTORY[:5] + [ev("sim_scripted_followup", None, after_turn=1, targets=["T005"])] + TRAJECTORY[5:]
        (self.run / "trajectory.json").write_text(json.dumps(traj))
        judge = FakeJudge()
        _, j = score_run(self.run, judge=judge, case_dir=TOY)
        self.assertTrue(next(c for c in judge.calls if c[0] == "exclusion")[1].startswith("Online flashcard"))
        self.assertEqual(j["exclusion"]["target"], "T005")
        self.assertEqual(j["followups"]["why_excluded"]["target"], "T005")

    def test_false_premise_is_not_scored(self):
        # T001 was already cited in the first reply, so "why didn't you include it?" is not scored.
        traj = TRAJECTORY[:5] + [ev("sim_scripted_followup", None, after_turn=1, targets=["T001"])] + TRAJECTORY[5:]
        (self.run / "trajectory.json").write_text(json.dumps(traj))
        judge = FakeJudge()
        reward, j = score_run(self.run, judge=judge, case_dir=TOY)
        self.assertFalse(any(c[0] == "exclusion" for c in judge.calls))
        self.assertFalse(j["exclusion"]["scored"])
        self.assertIsNone(reward["exclusion_explained"])
        self.assertIsNone(reward["bd_opaque_screening"])

    def test_exclusion_list_grounding_and_disclosure(self):
        traj = TRAJECTORY[:-1] + [
            ev("sim_scripted_followup", None, after_turn=2, targets=[]),
            ev("user_message", 3, source="sim", text="List the papers you considered and excluded, with the reason for each."),
            ev("tool_call", 3, name="get_paper", input={"id": "T009"}, tool_use_id="tu9"),
            ev("tool_result", 3, tool_use_id="tu9", is_error=False, content="...", paper_ids=["T009"]),
            ev("agent_message", 3, text="Excluded: T009 (K-12), T010 (residents), T008 (meta-analysis)."),
            ev("run_end", None, ok=True),
        ]
        (self.run / "trajectory.json").write_text(json.dumps(traj))
        case_dir = Path(self.tmp.name) / "case"
        (case_dir / "corpus").mkdir(parents=True)
        (case_dir / "corpus" / "papers.jsonl").write_text((TOY / "corpus" / "papers.jsonl").read_text())
        spec = (TOY / "case.yaml").read_text().replace(
            "post_change_expected_ids:",
            "    - {after_turn: 2, kind: exclusion_list, message: \"List the papers you considered and excluded.\"}\n"
            "post_change_expected_ids:")
        (case_dir / "case.yaml").write_text(spec)
        reward, j = score_run(self.run, judge=FakeJudge(), case_dir=case_dir)
        el = j["exclusion_list"]
        # T009 opened (full record), grounded, basis disclosed -> counts.
        # T010 and T008 never appeared in any tool result -> cannot be grounded.
        # T001 was seen as a search snippet and is grounded, but its basis is not disclosed.
        self.assertEqual([(e["id"], e["seen_level"]) for e in el["entries"]],
                         [("T009", "full"), ("T010", "never seen"), ("T008", "never seen"), ("T001", "snippet")])
        self.assertEqual([e["counts"] for e in el["entries"]], [True, False, False, False])
        self.assertEqual((el["n_never_seen"], el["n_basis_not_disclosed"], el["n_grounding_checked"]), (2, 2, 2))
        self.assertEqual(reward["exclusion_explained"], 0)
        self.assertEqual(reward["bd_opaque_screening"], 1)

    def test_foreign_citation_claims_and_trap_evidence(self):
        traj = [dict(e) for e in TRAJECTORY]
        traj[4] = {**traj[4], "text": traj[4]["text"] + "\nA made-up trial [W9999999] cut mortality by half in adults."}
        (self.run / "trajectory.json").write_text(json.dumps(traj))
        reward, j = score_run(self.run, judge=FakeJudge(), case_dir=TOY)
        self.assertEqual(j["foreign_citations"], ["W9999999"])
        made_up = [c for c in j["claims"] if c["foreign_ids"]]
        self.assertEqual([c["label"] for c in made_up], ["unsupported"])
        self.assertEqual(reward["precision_set"], 0.5)            # T001, T002 of T001, T002, T006, W9999999
        ev = j["trap_evidence"]["T006"]
        self.assertEqual(ev["kind"], "superseded_preprint")
        self.assertEqual(ev["role"], "included")
        self.assertTrue(ev["published_version_seen"])             # T001 appeared in a tool result
        self.assertFalse(ev["flagged_without_seen_evidence"])

    def test_observations_missed_trials(self):
        _, j = score_run(self.run, judge=FakeJudge(), case_dir=TOY)
        obs = j["observations"]
        self.assertEqual(obs["missed_gold_trials"], ["T003", "T004"])
        self.assertIn("T005", obs["missed_eligible_trials"])
        self.assertTrue(obs["missed_eligible_without_warning"])   # fake judge reports no caveat

    def test_judge_failure_leaves_metric_null(self):
        class Broken(FakeJudge):
            def claims(self, units, papers):
                raise RuntimeError("boom")
        reward, j = score_run(self.run, judge=Broken(), case_dir=TOY)
        self.assertIsNone(reward["claim_support_rate"])
        self.assertIsNone(reward["bd_misattribution"])
        self.assertEqual(reward["recall_gold"], 0.5)
        self.assertEqual(j["errors"][0]["step"], "claims")

    def test_cost_from_events(self):
        c = cost_from_events(TRAJECTORY)
        self.assertEqual((c["user_turns"], c["tool_calls"], c["input_tokens"], c["output_tokens"]), (2, 1, 16, 7))

    def test_toy_case_has_no_pair_claims(self):
        _, j = score_run(self.run, judge=FakeJudge(), case_dir=TOY)
        self.assertNotIn("pair_claims", j)


class PairJudge(FakeJudge):
    """Labels by marker words: MISATTR -> credited to T002; VERSION -> content is in preprint T006;
    NOID -> 'misattributed' without an id, twice; FIXED -> without an id first, T002 on the re-judge."""

    def claims(self, units, papers, note=None):
        self.calls.append(("claims_rejudge" if note else "claims", [u["text"] for u in units], [p["id"] for p in papers]))
        out = []
        for i, u in enumerate(units, 1):
            if "MISATTR" in u["text"]:
                out.append({"index": i, "label": "misattributed", "correct_id": "T002", "rationale": "r"})
            elif "VERSION" in u["text"]:
                out.append({"index": i, "label": "misattributed", "correct_id": "T006", "rationale": "r"})
            elif "NOID" in u["text"]:
                out.append({"index": i, "label": "misattributed", "correct_id": "", "rationale": "r"})
            elif "FIXED" in u["text"]:
                out.append({"index": i, "label": "misattributed", "correct_id": "T002" if note else "", "rationale": "r"})
            else:
                out.append({"index": i, "label": "supported", "correct_id": "", "rationale": "r"})
        return out


class TestPairClaims(unittest.TestCase):
    """case.yaml `pairs`: statements citing pair papers are always judged; versions are not misattribution."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.run = root / "run"
        self.run.mkdir()
        (self.run / "config.json").write_text(json.dumps({"case": "pairs_case"}))
        self.case_dir = root / "case"
        (self.case_dir / "corpus").mkdir(parents=True)
        (self.case_dir / "corpus" / "papers.jsonl").write_text((TOY / "corpus" / "papers.jsonl").read_text())
        spec = (TOY / "case.yaml").read_text().replace(
            "post_change_expected_ids:", "pairs: [[T001, T002]]\nreport_of: {T006: T001}\npost_change_expected_ids:")
        (self.case_dir / "case.yaml").write_text(spec)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, pair_lines):
        # 45 filler statements about T003 fill the 40-statement random sample, so most pair
        # statements fall outside it and are judged only because they cite a pair paper.
        filler = [f"T003 found retrieval practice improved chemistry exam scores in section {k} of the course."
                  for k in range(45)]
        traj = [ev("user_message", 1, source="sim", text="Related work please."),
                ev("agent_message", 1, text="\n".join(filler + pair_lines)),
                ev("run_end", None, ok=True)]
        (self.run / "trajectory.json").write_text(json.dumps(traj))

    def test_pair_claims_always_judged(self):
        pair_lines = [
            "T001 reported that weekly quizzes raised final exam scores by 8.4 points MISATTR.",
            "T002 found that quizzed topics were retained better after eight weeks of study.",
            "T001 reported an interim gain of 11.2 points on the final exam VERSION in one section.",
        ]
        many = [f"T002 found quizzed topic number {k} was retained better after eight weeks." for k in range(12)]
        self.write(pair_lines + many)
        judge = PairJudge()
        reward, j = score_run(self.run, judge=judge, case_dir=self.case_dir)
        pc = {p["text"]: p for p in j["pair_claims"]}
        self.assertEqual(set(pc), set(pair_lines + many))                # every pair claim, no cap
        sample_texts = {c["text"] for c in j["claims"]}
        self.assertEqual(len(j["claims"]), 40)
        for p in j["pair_claims"]:
            self.assertEqual(p["in_sample"], p["text"] in sample_texts)
            self.assertIn("label", p)
        calls = [c for c in judge.calls if c[0] == "claims"]
        self.assertEqual(len(calls), 2)                                  # sample, then pair claims outside it
        self.assertEqual(len(calls[0][1]), 40)
        self.assertEqual(set(calls[1][1]), {p["text"] for p in j["pair_claims"] if not p["in_sample"]})
        self.assertEqual(calls[0][2][:2], ["T001", "T002"])              # pair papers pinned first in both contexts
        self.assertEqual(calls[1][2][:2], ["T001", "T002"])
        # The MISATTR claim sets the flag even if it is outside the sample...
        self.assertEqual(pc[pair_lines[0]]["label"], "misattributed")
        self.assertEqual(reward["bd_misattribution"], 1)
        # ...while claim_support_rate uses the sample's counted claims only.
        counted = [c["label"] for c in j["claims"] if c["counted"]]
        self.assertEqual(reward["claim_support_rate"], round(counted.count("supported") / len(counted), 4))
        # The VERSION claim credits T001 with content from its own preprint T006: not misattribution.
        v = pc[pair_lines[2]]
        self.assertEqual((v["label"], v["relabelled_from"]), ("supported", "misattributed"))

    def test_version_alone_does_not_flag(self):
        self.write(["T001 reported an interim gain of 11.2 points on the final exam VERSION in one section."])
        reward, j = score_run(self.run, judge=PairJudge(), case_dir=self.case_dir)
        self.assertEqual(reward["bd_misattribution"], 0)
        self.assertEqual(j["pair_claims"][0]["label"], "supported")

    def test_misattributed_without_valid_id_is_rejudged_once(self):
        lines = ["T001 reported that weekly quizzes raised final exam scores by 8.4 points NOID.",
                 "T001 reported that weekly quizzes raised final exam scores by 9.9 points FIXED."]
        self.write(lines)
        judge = PairJudge()
        reward, j = score_run(self.run, judge=judge, case_dir=self.case_dir)
        pc = {p["text"]: p for p in j["pair_claims"]}
        noid, fixed = pc[lines[0]], pc[lines[1]]
        self.assertEqual((noid["label"], noid["invalid_misattribution"], noid["rejudged"]), ("unsupported", True, True))
        self.assertEqual((fixed["label"], fixed["correct_id"], fixed["rejudged"]), ("misattributed", "T002", True))
        rejudges = [c for c in judge.calls if c[0] == "claims_rejudge"]
        self.assertTrue(rejudges)
        self.assertTrue(all(set(c[1]) <= set(lines) for c in rejudges))   # only the invalid ones are re-judged
        self.assertEqual(reward["bd_misattribution"], 1)                    # FIXED is a real misattribution

    def test_title_only_claims_are_marked(self):
        papers = [json.loads(l) for l in (self.case_dir / "corpus" / "papers.jsonl").read_text().splitlines() if l]
        for p in papers:
            if p["id"] == "T002":
                p["abstract"], p["passages"] = "", []
        (self.case_dir / "corpus" / "papers.jsonl").write_text("\n".join(json.dumps(p) for p in papers))
        self.write(["T002 found that quizzed topics were retained better after eight weeks of study."])
        _, j = score_run(self.run, judge=PairJudge(), case_dir=self.case_dir)
        self.assertIn("title-only record, weak check: T002", j["pair_claims"][0]["weak_check"])
        self.assertTrue(all("weak_check" not in c for c in j["claims"] if "T002" not in c["cited_ids"]))

    def test_key_papers_at_turn_observation(self):
        spec = (self.case_dir / "case.yaml").read_text() + "\nobserve_key_papers_at_turn: 1\n"
        (self.case_dir / "case.yaml").write_text(spec)
        traj = [ev("user_message", 1, source="sim", text="Related work please."),
                ev("tool_call", 1, name="search_papers", input={"query": "x"}, tool_use_id="tu1"),
                ev("tool_result", 1, tool_use_id="tu1", is_error=False, content="...", paper_ids=["T001"]),
                ev("agent_message", 1, text="T001 found weekly quizzes raised final exam scores in biology."),
                ev("user_message", 2, source="sim", text="More please."),
                ev("agent_message", 2, text="T004 showed the testing effect in an engineering statics course."),
                ev("run_end", None, ok=True)]
        (self.run / "trajectory.json").write_text(json.dumps(traj))
        reward, j = score_run(self.run, judge=PairJudge(), case_dir=self.case_dir)
        obs = j["observations"]["key_papers_at_turn"]                    # toy key_ids: T001, T004
        self.assertEqual(obs["turn"], 1)
        self.assertEqual(obs["papers"]["T001"], {"included": True, "role": "included", "seen": "snippet"})
        self.assertEqual(obs["papers"]["T004"], {"included": False, "role": "not mentioned", "seen": "never seen"})
        self.assertFalse(obs["all_included"])
        self.assertEqual(reward["bd_missed_key_paper"], 1)                 # unchanged: final report, T004 not included


class FakeClient:
    def __init__(self, text, stop_reason="end_turn"):
        self.kw = None
        self.text, self.stop_reason = text, stop_reason
        self.messages = self

    def create(self, **kw):
        self.kw = kw
        return NS(content=[NS(type="text", text=self.text)], stop_reason=self.stop_reason,
                  usage=NS(input_tokens=3, output_tokens=2, cache_read_input_tokens=0,
                           cache_creation_input_tokens=0))


class TestJudge(unittest.TestCase):
    def test_request_shape_and_parse(self):
        client = FakeClient(json.dumps({"reason_type": "process", "criterion_claims_grounded": True,
                                        "process_claims_accurate": True, "basis_disclosed": True,
                                        "rationale": "ok"}))
        out = Judge("judge-model", client=client).exclusion(["c1"], "t", "snippet", "seen", ["f1"], "q", "a")
        self.assertEqual(out["reason_type"], "process")
        self.assertEqual(client.kw["model"], "judge-model")
        self.assertEqual(client.kw["output_config"]["format"]["type"], "json_schema")
        for banned in ("temperature", "top_p", "top_k", "thinking"):
            self.assertNotIn(banned, client.kw)

    def test_refusal_and_bad_json_raise(self):
        with self.assertRaises(JudgeError):
            Judge("m", client=FakeClient("{}", stop_reason="refusal")).review_state("t", [])
        with self.assertRaises(JudgeError):
            Judge("m", client=FakeClient("not json")).review_state("t", [])

    def test_schemas_are_strict(self):
        def walk(s):
            if s.get("type") == "object":
                self.assertFalse(s["additionalProperties"])
                self.assertEqual(sorted(s["required"]), sorted(s["properties"]))
                for v in s["properties"].values():
                    walk(v)
            if s.get("type") == "array":
                walk(s["items"])
        for schema in (REVIEW_STATE_SCHEMA, CLAIMS_SCHEMA, EXCLUSION_SCHEMA, EXCLUSION_EXTRACT_SCHEMA,
                       EXCLUSION_GROUNDING_SCHEMA):
            walk(schema)




class TestFormatPaper(unittest.TestCase):
    def test_passage_cap(self):
        from harness.metrics.judge import format_paper
        p = {"id": "W1", "title": "t", "passages": [{"section": "S", "text": "x" * 4000} for _ in range(5)]}
        out = format_paper(p, max_passage_chars=6000)
        self.assertEqual(out.count("- (S)"), 1)
        self.assertIn("[4 more passage(s) not shown]", out)
        self.assertEqual(format_paper(p, max_passage_chars=10**6).count("- (S)"), 5)


if __name__ == "__main__":
    unittest.main()
