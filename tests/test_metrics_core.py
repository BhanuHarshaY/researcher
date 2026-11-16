"""Unit tests for harness/metrics/core.py with small synthetic inputs."""
import unittest

from harness.metrics import core
from harness.metrics.names import ALL_METRICS

CORPUS = {"A", "B", "C", "D", "O1", "O2", "R", "P", "Z"}
CASE = {
    "gold_ids": ["A", "B", "C", "X_NOT_IN_CORPUS"],
    "key_ids": ["A", "C"],
    "relevant_ids": ["A", "B", "C", "D"],
    "off_scope_ids": ["O1", "O2"],
    "traps": [
        {"id": "R", "kind": "retracted"},
        {"id": "P", "kind": "superseded_preprint"},
        {"id": "GONE", "kind": "retracted"},  # not in corpus: ignored
    ],
    "post_change_expected_ids": ["A", "B", "D"],
    "thresholds": {"off_scope": 0.2, "steer_preservation": 0.7},
}


class TestSetMetrics(unittest.TestCase):
    def test_recall_gold_uses_findable_gold_only(self):
        self.assertEqual(core.recall_gold({"A", "B", "Z"}, CASE["gold_ids"], CORPUS), round(2 / 3, 4))
        self.assertIsNone(core.recall_gold({"A"}, ["NOPE"], CORPUS))

    def test_precision_and_off_scope(self):
        cited = {"A", "B", "O1", "Z"}
        self.assertEqual(core.precision_set(cited, CASE["relevant_ids"]), 0.5)
        self.assertEqual(core.off_scope_rate(cited, CASE["off_scope_ids"]), 0.25)
        self.assertIsNone(core.precision_set(set(), CASE["relevant_ids"]))
        self.assertIsNone(core.off_scope_rate(set(), CASE["off_scope_ids"]))

    def test_claim_support_rate_ignores_not_a_claim(self):
        labels = ["supported", "unsupported", "not_a_claim", "misattributed", "supported"]
        self.assertEqual(core.claim_support_rate(labels), 0.5)
        self.assertIsNone(core.claim_support_rate(["not_a_claim"]))
        self.assertIsNone(core.claim_support_rate([]))

    def test_trap_flag_rate_and_status_ignored(self):
        roles = {"R": "included", "P": "included"}
        flagged = {"R": True, "P": False}
        self.assertEqual(core.trap_flag_rate(CASE["traps"], CORPUS, roles, flagged), 0.5)
        self.assertEqual(core.status_ignored(CASE["traps"], CORPUS, roles, flagged), 1)
        # Excluded or never mentioned counts as handled.
        roles = {"R": "excluded"}
        self.assertEqual(core.trap_flag_rate(CASE["traps"], CORPUS, roles, {}), 1.0)
        self.assertEqual(core.status_ignored(CASE["traps"], CORPUS, roles, {}), 0)
        # "mentioned" in passing is not citing.
        self.assertEqual(core.status_ignored(CASE["traps"], CORPUS, {"P": "mentioned"}, {}), 0)
        self.assertIsNone(core.trap_flag_rate([], CORPUS, roles, {}))
        self.assertIsNone(core.status_ignored([{"id": "GONE", "kind": "retracted"}], CORPUS, {}, {}))

    def test_steer_preservation(self):
        pre, post = {"A", "B", "C", "O1"}, {"A", "D"}
        # should keep = pre & expected = {A, B}; kept = {A}
        self.assertEqual(core.steer_preservation(pre, post, CASE["post_change_expected_ids"]), 0.5)
        self.assertIsNone(core.steer_preservation(None, post, ["A"]))
        self.assertIsNone(core.steer_preservation(pre, post, []))
        self.assertIsNone(core.steer_preservation({"O1"}, post, ["A"]))  # nothing should be kept

    def test_missed_key_paper(self):
        self.assertEqual(core.missed_key_paper({"A"}, ["A", "C"]), 1)
        self.assertEqual(core.missed_key_paper({"A", "C"}, ["A", "C"]), 0)
        self.assertIsNone(core.missed_key_paper({"A"}, []))


class TestComputeReward(unittest.TestCase):
    def test_full_reward(self):
        final = {"A": "included", "B": "included", "O1": "included", "O2": "excluded",
                 "R": "included", "P": "mentioned", "C": "mentioned"}
        pre = {"A": "included", "B": "included", "D": "included"}
        cost = {"user_turns": 3, "tool_calls": 12, "input_tokens": 100, "output_tokens": 50,
                "wall_time_s": 1.5, "not_a_metric": 9}
        r = core.compute_reward(CASE, CORPUS, final_roles=final, flagged={"R": False}, pre_roles=pre,
                                claim_labels=["supported", "misattributed", "supported"],
                                exclusion_explained=0, cost=cost)
        self.assertEqual(list(r), list(ALL_METRICS))  # fixed names, fixed order
        self.assertEqual(r["recall_gold"], round(2 / 3, 4))           # A, B of A, B, C
        self.assertEqual(r["precision_set"], 0.5)                       # A, B of A, B, O1, R
        self.assertEqual(r["off_scope_rate"], 0.25)
        self.assertEqual(r["bd_scope_drift"], 1)                        # 0.25 > 0.2
        self.assertEqual(r["trap_flag_rate"], 0.5)                      # R unflagged, P only mentioned
        self.assertEqual(r["bd_status_ignored"], 1)
        self.assertEqual(r["bd_missed_key_paper"], 1)                   # C missing
        self.assertEqual(r["steer_preservation"], round(2 / 3, 4))     # A, B kept of A, B, D
        self.assertEqual(r["bd_cant_steer"], 1)                         # 0.667 < 0.7
        self.assertEqual(r["claim_support_rate"], round(2 / 3, 4))
        self.assertEqual(r["bd_misattribution"], 1)
        self.assertEqual(r["exclusion_explained"], 0)
        self.assertEqual(r["bd_opaque_screening"], 1)
        self.assertEqual(r["tool_calls"], 12)
        self.assertNotIn("not_a_metric", r)

    def test_nulls_when_judgments_missing(self):
        r = core.compute_reward(CASE, CORPUS, final_roles=None, flagged=None, pre_roles=None,
                                claim_labels=None, exclusion_explained=None)
        self.assertTrue(all(v is None for v in r.values()))

    def test_no_change_no_steer_and_clean_run(self):
        final = {"A": "included", "C": "included", "R": "included", "P": "excluded"}
        r = core.compute_reward(CASE, CORPUS, final_roles=final, flagged={"R": True}, pre_roles=None,
                                claim_labels=["not_a_claim"], exclusion_explained=1)
        self.assertIsNone(r["steer_preservation"])
        self.assertIsNone(r["bd_cant_steer"])
        self.assertEqual(r["bd_status_ignored"], 0)
        self.assertEqual(r["trap_flag_rate"], 1.0)
        self.assertEqual(r["bd_missed_key_paper"], 0)
        self.assertEqual(r["bd_scope_drift"], 0)
        self.assertIsNone(r["claim_support_rate"])
        self.assertIsNone(r["bd_misattribution"])                       # nothing checked
        self.assertEqual(r["bd_opaque_screening"], 0)


class TestConversationParsing(unittest.TestCase):
    def test_classify_followups_inferred(self):
        case = {"post_change_expected_ids": ["A"], "script": {"followups": [
            {"after_turn": 1, "message": 'Why didn\'t you include "{title:W9}"?'},
            {"after_turn": 2, "message": "Please tighten the scope: exclude preprints."},
        ]}}
        fu = core.classify_followups(case)
        self.assertEqual(fu["why_excluded"], {"user_turn": 2, "target": "W9"})
        self.assertEqual(fu["criteria_change"], {"user_turn": 3})

    def test_classify_followups_explicit_and_none(self):
        case = {"script": {"followups": [
            {"after_turn": 2, "kind": "why_excluded", "target": "W1", "message": "Where is {id:W1}?"}]}}
        self.assertEqual(core.classify_followups(case)["why_excluded"], {"user_turn": 3, "target": "W1"})
        self.assertIsNone(core.classify_followups(case)["criteria_change"])
        self.assertEqual(core.classify_followups({}), {"why_excluded": None, "criteria_change": None})

    def test_conversation(self):
        ev = [{"type": "user_message", "turn": 1, "text": "q"}, {"type": "tool_call", "turn": 1},
              {"type": "agent_message", "turn": 1, "text": "a"}, {"type": "user_message", "turn": 2, "text": "q2"}]
        self.assertEqual(core.conversation(ev), [{"turn": 1, "user": "q", "agent": "a"},
                                                 {"turn": 2, "user": "q2", "agent": None}])


def _find(text):
    import re
    return list(dict.fromkeys(re.findall(r"(?<![A-Za-z0-9])W\d+(?![A-Za-z0-9])", text)))


class TestClaimUnits(unittest.TestCase):
    MSG = (
        "## Included\n"
        "**Included:** W1, W2, W3.\n"
        "| ID | Design | Finding |\n|---|---|---|\n"
        "| W1 (2019) | RCT, n = 412 | Quiz group scored 8.4 points higher on the final exam |\n"
        "- W2 found that quizzed topics were retained better after eight weeks. This was a crossover study.\n"
        "Overall the evidence favors retrieval practice, as shown in [W1] and [W3] across several courses.\n"
        "This sentence has no id but is long enough to count as a claim otherwise.\n"
    )

    def test_units_need_an_id_and_enough_words(self):
        units = core.claim_units([(1, self.MSG)], _find)
        by_start = {u["text"][:8]: u for u in units}
        texts = [u["text"] for u in units]
        self.assertEqual(len(units), 3)
        self.assertIn("| W1 (20", by_start)                              # table row
        self.assertIn("W2 found", by_start)                              # bullet marker stripped, split at "."
        self.assertEqual(by_start["Overall "]["cited_ids"], ["W1", "W3"])
        self.assertFalse(any("Included:" in t for t in texts))          # bare id list skipped

    def test_dedupe_and_deterministic_cap(self):
        msgs = [(t, f"Paper W{i} reported a large improvement in final exam scores overall.")
                for t in (1, 2) for i in range(20)]
        a = core.claim_units(msgs, _find, max_candidates=15)
        b = core.claim_units(msgs, _find, max_candidates=15)
        self.assertEqual(len(a), 15)                                     # 20 unique after dedupe, capped
        self.assertEqual(a, b)                                           # fixed seed: same order
        self.assertEqual(len(core.claim_units(msgs, _find)), 20)         # default cap is 40

    def test_counted_claims_takes_first_15_checkable(self):
        labels = ["not_a_claim", "supported"] * 20                       # 20 checkable among 40
        mask = core.counted_claims(labels)
        self.assertEqual(sum(mask), 15)
        self.assertFalse(mask[0])
        self.assertTrue(mask[1])
        self.assertEqual(mask.index(False, 30), 30)                      # 15th checkable is index 29
        self.assertEqual(sum(core.counted_claims(["supported", "not_a_claim"])), 1)


if __name__ == "__main__":
    unittest.main()
