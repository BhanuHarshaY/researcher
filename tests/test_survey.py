"""survey.py: answers, validation, skip/EOF handling, scores, and sync with shared/survey_interview.md."""
import io
import json
import tempfile
import unittest
from pathlib import Path

from harness.config import REPO_ROOT
from harness.survey import survey


class TestSurvey(unittest.TestCase):
    def run_with(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        result = survey.run_survey(tmp.name, inp=io.StringIO(text), out=io.StringIO())
        saved = json.loads((Path(tmp.name) / "survey.json").read_text())
        self.assertEqual(saved["scores"], result["scores"])
        return result

    def test_full_survey_with_invalid_and_skipped_answers(self):
        # TLX: 50, 40, (abc, 101 rejected) 30, 20, 10 ; Likert: 7, 6, skip, 5, 4, 3, 2, (0 rejected) 1
        r = self.run_with("P01\n50\n40\nabc\n101\n30\n20\n10\n7\n6\ns\n5\n4\n3\n2\n0\n1\n")
        self.assertTrue(r["completed"])
        self.assertEqual(r["participant_id"], "P01")
        self.assertEqual(r["nasa_tlx"], {"mental_demand": 50, "temporal_demand": 40, "performance": 30,
                                         "effort": 20, "frustration": 10})
        self.assertEqual([i["response"] for i in r["likert"]], [7, 6, None, 5, 4, 3, 2, 1])
        self.assertEqual(r["scores"], {"raw_tlx": 30.0, "controllability": 6.0, "trust": 3.0,
                                       "over_reliance": 3, "item6_reversed": 5, "engagement": 1})
        self.assertTrue(r["likert"][5]["reverse_coded"])

    def test_eof_saves_partial(self):
        r = self.run_with("P02\n50\n")
        self.assertFalse(r["completed"])
        self.assertEqual(r["nasa_tlx"]["mental_demand"], 50)
        self.assertIsNone(r["nasa_tlx"]["temporal_demand"])
        self.assertIsNone(r["scores"]["controllability"])

    def test_interview_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = survey.write_interview_template(tmp, {"case": "c", "agent": "baseline"}, "P01")
            text = p.read_text()
        self.assertIn("Participant ID: P01", text)
        for q in survey.INTERVIEW:
            self.assertIn(q, text)

    def test_questions_match_shared_doc(self):
        doc = (REPO_ROOT / "shared" / "survey_interview.md").read_text()
        for _k, label, q, lo, hi in survey.NASA_TLX:
            self.assertIn(f"| {label} | {q} | {lo} | {hi} |", doc)
        for n, _c, text, _r in survey.LIKERT:
            self.assertIn(f"{n}. {text}", doc)
        for i, q in enumerate(survey.INTERVIEW, 1):
            self.assertIn(f"{i}. {q}", doc)


if __name__ == "__main__":
    unittest.main()
