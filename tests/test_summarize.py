"""summarize.py: aggregation, breakdown counts and rerun_overlap."""
import json
import tempfile
import unittest
from pathlib import Path

from harness.metrics import summarize
from harness.metrics.names import null_reward


def make_run(mode_dir: Path, name: str, included, **metrics):
    d = mode_dir / name
    d.mkdir(parents=True)
    r = null_reward()
    r.update(metrics)
    (d / "reward.json").write_text(json.dumps(r))
    if included is not None:
        (d / "judgments.json").write_text(json.dumps({"included_ids": included}))


class TestSummarize(unittest.TestCase):
    def test_jaccard(self):
        self.assertEqual(summarize.jaccard({"A"}, {"A"}), 1.0)
        self.assertEqual(summarize.jaccard(set(), set()), 1.0)
        self.assertEqual(summarize.jaccard({"A", "B"}, {"A", "C"}), 1 / 3)
        self.assertIsNone(summarize.rerun_overlap([{"A"}]))

    def test_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp)
            make_run(md, "20261116T100000Z_1", ["A", "B"], recall_gold=0.5, bd_missed_key_paper=1, tool_calls=10)
            make_run(md, "20261116T100100Z_2", ["A", "B"], recall_gold=1.0, bd_missed_key_paper=0, tool_calls=20)
            make_run(md, "20261116T100200Z_3", ["A", "C"], recall_gold=None, bd_missed_key_paper=1, tool_calls=30)
            make_run(md, "20261116T100300Z_4", None, recall_gold=0.0, tool_calls=40)   # no judgments
            (md / "not_a_run").mkdir()

            runs = summarize.load_runs(md)
            self.assertEqual(len(runs), 4)
            s = summarize.summarize(runs)
            self.assertEqual(s["metrics"]["recall_gold"]["mean"], 0.5)        # mean of 0.5, 1.0, 0.0
            self.assertEqual(s["metrics"]["recall_gold"]["n"], 3)
            self.assertEqual(s["metrics"]["tool_calls"]["mean"], 25)
            self.assertEqual(s["breakdowns"]["bd_missed_key_paper"], {"runs_flagged": 2, "n": 3})
            self.assertEqual(s["breakdowns"]["bd_misattribution"], {"runs_flagged": 0, "n": 0})
            self.assertEqual(s["rerun_overlap"], round((1 + 1 / 3 + 1 / 3) / 3, 4))
            self.assertEqual(s["rerun_overlap_n"], 3)

            last2 = summarize.summarize(summarize.load_runs(md, last=2))
            self.assertEqual(last2["runs"], ["20261116T100200Z_3", "20261116T100300Z_4"])

            text = summarize.to_markdown("c", "baseline", "sim", s, runs)
            self.assertIn("| `bd_missed_key_paper` | 2 of 3 |", text)
            self.assertIn("| `bd_misattribution` | n/a |", text)
            self.assertIn("rerun_overlap", text)


if __name__ == "__main__":
    unittest.main()
