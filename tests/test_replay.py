"""replay.py: stored judge answers replayed through score_run reproduce the stored scores."""
import json
import tempfile
import unittest
from pathlib import Path

from harness.metrics.replay import replay_run
from harness.metrics.score import score_run, write_scores
from tests.test_score import TOY, TRAJECTORY, FakeJudge


class TestReplay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name)
        (self.run / "config.json").write_text(json.dumps({"case": "_toy"}))
        (self.run / "trajectory.json").write_text(json.dumps(TRAJECTORY))
        reward, j = score_run(self.run, judge=FakeJudge(), case_dir=TOY)
        write_scores(self.run, reward, j)

    def tearDown(self):
        self.tmp.cleanup()

    def test_replay_matches_stored_scores(self):
        reward, _, reward_diff, judgments_diff = replay_run(self.run)
        self.assertEqual(reward_diff, [])
        self.assertEqual(judgments_diff, [])
        self.assertEqual(reward["bd_misattribution"], 1)

    def test_replay_reports_changes(self):
        j = json.loads((self.run / "judgments.json").read_text())
        j["claims"][0].pop("counted")          # as if scored by older code that didn't write it
        (self.run / "judgments.json").write_text(json.dumps(j))
        _, _, reward_diff, judgments_diff = replay_run(self.run)
        self.assertEqual(reward_diff, [])
        self.assertEqual(judgments_diff, [".claims[0].counted: added by current code"])


if __name__ == "__main__":
    unittest.main()
