"""mock_search.py: determinism, hidden papers, status visibility, id finding."""
import json
import unittest

from harness.config import CASES_DIR
from harness.tools.mock_search import MockSearch

CORPUS = CASES_DIR / "_toy" / "corpus" / "papers.jsonl"


class TestMockSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = MockSearch(CORPUS)

    def search(self, **kw):
        text, err = self.s.execute("search_papers", kw)
        self.assertFalse(err)
        return json.loads(text)["results"]

    def test_deterministic_and_ranked(self):
        a = self.s.execute("search_papers", {"query": "retrieval practice undergraduate exam"})
        self.assertEqual(a, self.s.execute("search_papers", {"query": "retrieval practice undergraduate exam"}))
        ids = [r["id"] for r in self.search(query="retrieval practice undergraduate exam")]
        self.assertEqual(ids, ["T007", "T005", "T006", "T001", "T003", "T002", "T010", "T009", "T008"])

    def test_hidden_paper_only_via_citations(self):
        for q in ["testing effect engineering statics", "statics", "retrieval practice", "randomized"]:
            self.assertNotIn("T004", [r["id"] for r in self.search(query=q, limit=50)])
        refs = json.loads(self.s.execute("get_references", {"id": "T001"})[0])["references"]
        self.assertIn("T004", [r["id"] for r in refs])
        cites = json.loads(self.s.execute("get_citations", {"id": "T008"})[0])["cited_by"]
        self.assertIn("T004", [r["id"] for r in cites])

    def test_status_visible_only_in_get_paper(self):
        for r in self.search(query="retrieval practice"):
            self.assertNotIn("status", r)
        p = json.loads(self.s.execute("get_paper", {"id": "T007"})[0])
        self.assertEqual(p["status"], "retracted")
        self.assertNotIn("synthetic", p)
        self.assertNotIn("hidden_from_search", p)

    def test_year_filter_and_errors(self):
        self.assertTrue(all(r["year"] >= 2021 for r in self.search(query="retrieval practice", year_from=2021)))
        self.assertTrue(self.s.execute("get_paper", {"id": "NOPE"})[1])
        self.assertTrue(self.s.execute("nope", {})[1])
        self.assertTrue(self.s.execute("search_papers", {"query": ""})[1])

    def test_find_ids(self):
        self.assertEqual(self.s.find_ids("See [T001], T002; T005–T010 and T0011 or XT003. [T004] T001"),
                         ["T001", "T002", "T005", "T010", "T004"])


if __name__ == "__main__":
    unittest.main()
