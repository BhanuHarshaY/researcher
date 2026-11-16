"""Mocked literature search over a frozen per-case corpus.

Tools exposed to agents (identical for baseline and proposed agents):
  search_papers(query, year_from=None, limit=20)  deterministic BM25 over title+abstract
  get_paper(id)                                    full record incl. status and passages
  get_references(id) / get_citations(id)           id+title lists (reach hidden papers)

No live search happens at run time. Any run-to-run variation comes from the
agent's choices, not from this database.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

SNIPPET_CHARS = 300
MAX_LIMIT = 50
BM25_K1 = 1.5
BM25_B = 0.75

# Fields that exist for the harness/metrics only and must never reach the agent.
INTERNAL_FIELDS = {"synthetic", "hidden_from_search"}

_STOPWORDS = frozenset(
    """a an and are as at be by for from has have in is it its of on or that the
    their this to was were with we our these those than then into via vs""".split()
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


TOOL_DEFS = [
    {
        "name": "search_papers",
        "description": (
            "Search the literature database by keyword. Ranks papers by relevance of "
            "title and abstract to the query. Returns id, title, year, venue and a short "
            "abstract snippet for each hit. Use get_paper for the full record."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword query."},
                "year_from": {
                    "type": ["integer", "null"],
                    "description": "Only return papers published in or after this year.",
                },
                "limit": {
                    "type": "integer",
                    "description": f"Max results (default 20, max {MAX_LIMIT}).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_paper",
        "description": (
            "Get the full record of a paper by id: metadata, publication status, "
            "abstract and available text passages."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "Paper id."}},
            "required": ["id"],
        },
    },
    {
        "name": "get_references",
        "description": "List the papers that a given paper cites (ids and titles).",
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "Paper id."}},
            "required": ["id"],
        },
    },
    {
        "name": "get_citations",
        "description": "List the papers that cite a given paper (ids and titles).",
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "Paper id."}},
            "required": ["id"],
        },
    },
]


class ToolError(Exception):
    """Raised for bad tool input; returned to the agent as an is_error tool_result."""


class MockSearch:
    def __init__(self, corpus_path: str | Path):
        self.corpus_path = Path(corpus_path)
        raw = self.corpus_path.read_bytes()
        self.corpus_sha256 = hashlib.sha256(raw).hexdigest()

        self.papers: dict[str, dict] = {}
        for lineno, line in enumerate(raw.decode("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec["id"] in self.papers:
                raise ValueError(f"{self.corpus_path}:{lineno}: duplicate id {rec['id']}")
            self.papers[rec["id"]] = rec

        # Citation graph, restricted to in-corpus ids. A paper's citations are the
        # union of its own cited_by list and every paper that lists it in references.
        self._refs: dict[str, list[str]] = {}
        cites: dict[str, set[str]] = {pid: set() for pid in self.papers}
        for pid, p in self.papers.items():
            self._refs[pid] = sorted({r for r in p.get("references", []) if r in self.papers})
            for r in self._refs[pid]:
                cites[r].add(pid)
            for c in p.get("cited_by", []):
                if c in self.papers:
                    cites[pid].add(c)
        self._cites = {pid: sorted(s) for pid, s in cites.items()}

        self._build_bm25()

    # ---------- BM25 index (searchable papers only) ----------
    def _build_bm25(self) -> None:
        self._doc_ids = sorted(
            pid for pid, p in self.papers.items() if not p.get("hidden_from_search", False)
        )
        self._doc_tf: dict[str, Counter] = {}
        self._doc_len: dict[str, int] = {}
        df: Counter = Counter()
        for pid in self._doc_ids:
            p = self.papers[pid]
            toks = tokenize(f"{p.get('title', '')} {p.get('abstract', '')}")
            tf = Counter(toks)
            self._doc_tf[pid] = tf
            self._doc_len[pid] = len(toks)
            df.update(tf.keys())
        n = len(self._doc_ids)
        self._avgdl = (sum(self._doc_len.values()) / n) if n else 0.0
        # Lucene-style idf, always positive.
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def _bm25(self, q_tokens: list[str], pid: str) -> float:
        tf = self._doc_tf[pid]
        dl = self._doc_len[pid]
        score = 0.0
        for t in q_tokens:
            f = tf.get(t, 0)
            if not f:
                continue
            denom = f + BM25_K1 * (1 - BM25_B + BM25_B * dl / (self._avgdl or 1))
            score += self._idf.get(t, 0.0) * f * (BM25_K1 + 1) / denom
        return score

    # ---------- tools ----------
    def _get(self, pid) -> dict:
        if not isinstance(pid, str) or pid not in self.papers:
            raise ToolError(f"No paper with id {pid!r} in the database.")
        return self.papers[pid]

    def search_papers(self, query: str, year_from: int | None = None, limit: int = 20) -> dict:
        if not isinstance(query, str) or not query.strip():
            raise ToolError("query must be a non-empty string.")
        if year_from is not None and not isinstance(year_from, int):
            raise ToolError("year_from must be an integer or null.")
        if not isinstance(limit, int) or limit < 1:
            raise ToolError("limit must be a positive integer.")
        limit = min(limit, MAX_LIMIT)

        q_tokens = tokenize(query)
        scored = []
        for pid in self._doc_ids:
            p = self.papers[pid]
            if year_from is not None and (p.get("year") or 0) < year_from:
                continue
            s = self._bm25(q_tokens, pid)
            if s > 0:
                scored.append((-round(s, 9), pid))
        scored.sort()  # score desc, then id asc: fully deterministic

        results = []
        for neg_s, pid in scored[:limit]:
            p = self.papers[pid]
            abstract = p.get("abstract", "") or ""
            snippet = abstract[:SNIPPET_CHARS] + ("..." if len(abstract) > SNIPPET_CHARS else "")
            # NOTE: status is deliberately NOT returned here (visible only via get_paper).
            results.append(
                {
                    "id": pid,
                    "title": p.get("title"),
                    "year": p.get("year"),
                    "venue": p.get("venue"),
                    "snippet": snippet,
                }
            )
        return {"query": query, "total_matches": len(scored), "results": results}

    def get_paper(self, id: str) -> dict:
        p = self._get(id)
        out = {k: v for k, v in p.items() if k not in INTERNAL_FIELDS | {"references", "cited_by"}}
        out["n_references"] = len(self._refs[id])
        out["n_citations"] = len(self._cites[id])
        out["note"] = "Use get_references / get_citations to list linked papers."
        return out

    def _id_title_list(self, ids: list[str]) -> list[dict]:
        return [
            {"id": i, "title": self.papers[i].get("title"), "year": self.papers[i].get("year")}
            for i in ids
        ]

    def get_references(self, id: str) -> dict:
        self._get(id)
        return {"id": id, "references": self._id_title_list(self._refs[id])}

    def get_citations(self, id: str) -> dict:
        self._get(id)
        return {"id": id, "cited_by": self._id_title_list(self._cites[id])}

    # ---------- dispatch ----------
    def execute(self, name: str, tool_input: dict) -> tuple[str, bool]:
        """Run a tool call. Returns (json_text, is_error)."""
        try:
            if not isinstance(tool_input, dict):
                raise ToolError("tool input must be an object.")
            if name == "search_papers":
                result = self.search_papers(
                    tool_input.get("query"),
                    tool_input.get("year_from"),
                    tool_input.get("limit", 20) if tool_input.get("limit") is not None else 20,
                )
            elif name == "get_paper":
                result = self.get_paper(tool_input.get("id"))
            elif name == "get_references":
                result = self.get_references(tool_input.get("id"))
            elif name == "get_citations":
                result = self.get_citations(tool_input.get("id"))
            else:
                raise ToolError(f"Unknown tool {name!r}.")
        except ToolError as e:
            return json.dumps({"error": str(e)}), True
        return json.dumps(result, ensure_ascii=False), False
