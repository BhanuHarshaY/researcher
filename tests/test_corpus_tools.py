"""corpus_tools: Semantic Scholar abstract fallback helpers and validate's new checks (no network)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from corpus_tools import snapshot, validate


class TestAbstractFallback(unittest.TestCase):
    def test_abstract_text(self):
        self.assertEqual(snapshot.s2_abstract_text({"abstract": "Abstract Even though algorithms..."}),
                         "")                                                     # truncated snippet
        self.assertEqual(snapshot.s2_abstract_text({"abstract": "Abstract Even though algorithms win."}),
                         "Even though algorithms win.")
        self.assertEqual(snapshot.s2_abstract_text({"abstract": "ABSTRACT: Text here."}), "Text here.")
        self.assertEqual(snapshot.s2_abstract_text({"abstract": None}), "")
        self.assertEqual(snapshot.s2_abstract_text(None), "")

    def test_frozen_file_means_no_request(self):
        with tempfile.TemporaryDirectory() as d:
            frozen = Path(d) / "s2_abstracts.json"
            frozen.write_text(json.dumps({"10.1/x": {"title": "T", "abstract": "A full abstract."}}))
            with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network used")):
                out = snapshot.s2_abstracts(["10.1/x"], frozen)
            self.assertEqual(out["10.1/x"]["abstract"], "A full abstract.")

    def test_missing_dois_are_fetched_once_and_frozen(self):
        class Resp:
            def __init__(self, body): self.body = body
            def read(self): return self.body
            def __enter__(self): return self
            def __exit__(self, *a): return False
        body = json.dumps([{"title": "New", "abstract": "Fetched abstract."}, None]).encode()
        with tempfile.TemporaryDirectory() as d:
            frozen = Path(d) / "s2_abstracts.json"
            with mock.patch("urllib.request.urlopen", return_value=Resp(body)) as m:
                out = snapshot.s2_abstracts(["10.1/new", "10.1/none"], frozen)
                self.assertEqual(m.call_count, 1)                                # one batched request
            self.assertEqual(out["10.1/new"]["abstract"], "Fetched abstract.")
            self.assertIsNone(out["10.1/none"]["abstract"])
            self.assertEqual(json.loads(frozen.read_text()), out)


class TestValidateChecks(unittest.TestCase):
    """Hidden papers must stay reachable; pair ids must be relevant; ranking must be known."""

    def make_case(self, root: Path, refs_to_a: bool, pairs, ranking="bm25"):
        d = root / "mini"
        (d / "corpus").mkdir(parents=True)
        papers = [
            {"id": "A", "title": "Hidden classic", "abstract": "x", "status": "published", "hidden_from_search": True,
             "references": [], "cited_by": []},
            {"id": "B", "title": "Searchable paper", "abstract": "y", "status": "published",
             "references": ["A"] if refs_to_a else [], "cited_by": []},
            {"id": "C", "title": "Off topic", "abstract": "z", "status": "published", "references": [], "cited_by": []},
        ]
        (d / "corpus" / "papers.jsonl").write_text("\n".join(json.dumps(p) for p in papers))
        (d / "case.yaml").write_text(yaml.safe_dump({
            "gold_ids": ["A"], "key_ids": ["A"], "relevant_ids": ["A", "B"], "off_scope_ids": ["C"],
            "traps": [], "pairs": pairs, "search_ranking": ranking}))
        return "mini"

    def run_validate(self, **kw):
        with tempfile.TemporaryDirectory() as t, mock.patch.object(validate, "CASES_DIR", Path(t)):
            return validate.validate(self.make_case(Path(t), **kw))

    def test_reachable_and_valid(self):
        self.assertEqual(self.run_validate(refs_to_a=True, pairs=[["A", "B"]]), [])

    def test_unreachable_hidden_paper(self):
        errs = self.run_validate(refs_to_a=False, pairs=[])
        self.assertTrue(any("unreachable" in e for e in errs), errs)

    def test_bad_pairs_and_ranking(self):
        errs = self.run_validate(refs_to_a=True, pairs=[["A", "C"], ["B", "B"]], ranking="pagerank")
        self.assertTrue(any("C is not in relevant_ids" in e for e in errs), errs)
        self.assertTrue(any("two different paper ids" in e for e in errs), errs)
        self.assertTrue(any("unknown search_ranking" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
