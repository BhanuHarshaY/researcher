"""Mocked literature search over a frozen per-case corpus.

Tools exposed to agents (identical for baseline and proposed agents):
  search_papers(query, year_from=None, limit=20)  deterministic BM25 over title+abstract
  get_paper(id)                                    metadata, abstract and passages
  get_references(id) / get_citations(id)           id+title lists (reach hidden papers)

Search ranking is set per case (`search_ranking` in case.yaml, recorded in
config.json):
  bm25            plain BM25 (default)
  bm25_citations  BM25 x (1 + CITATION_BOOST * ln(1 + in-corpus citations)): a small
                  boost for papers cited more often, as real scholarly search engines
                  apply. The count is the n_citations that get_paper shows.

Publication status is NOT shown by any tool, matching how status appears in
real sources: a retraction is a separate notice record (it cites the retracted
paper, so it shows up in search and in get_citations), and a superseded
preprint is a separate record from its journal version. The corpus keeps
`status` and `published_version_id` for the metrics only.

No live search happens at run time. Any run-to-run variation comes from the
agent's choices, not from this database.
"""
from __future__ import annotations

import copy
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
RANKINGS = ("bm25", "bm25_citations")
CITATION_BOOST = 0.1  # bm25_citations: x1.0 at 0 citations, x1.24 at 10, x1.46 at 100

# Fields that exist for the harness/metrics only and must never reach the agent.
INTERNAL_FIELDS = {"synthetic", "hidden_from_search", "status", "published_version_id", "notice_for"}

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
            "Get the full record of a paper by id: metadata (authors, venue, date, DOI), "
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

_SEARCH_DESCRIPTION_CITATIONS = (
    "Search the literature database by keyword. Ranks papers by relevance of "
    "title and abstract to the query, with a small boost for papers that are cited "
    "more often. Returns id, title, year, venue and a short abstract snippet for "
    "each hit. Use get_paper for the full record."
)


def tool_defs(ranking: str = "bm25") -> list[dict]:
    """Tool definitions for a ranking. bm25 returns TOOL_DEFS unchanged; the
    search description says so when citations affect the ranking."""
    if ranking not in RANKINGS:
        raise ValueError(f"unknown search_ranking {ranking!r}; expected one of {RANKINGS}")
    if ranking == "bm25":
        return TOOL_DEFS
    defs = copy.deepcopy(TOOL_DEFS)
    defs[0]["description"] = _SEARCH_DESCRIPTION_CITATIONS
    return defs


class BM25:
    """Deterministic Okapi BM25 over {id: text}. Ties sort by id."""

    def __init__(self, docs: dict[str, str], k1: float = BM25_K1, b: float = BM25_B):
        self.k1, self.b = k1, b
        self.ids = sorted(docs)
        self.tf: dict[str, Counter] = {}
        self.dl: dict[str, int] = {}
        df: Counter = Counter()
        for pid in self.ids:
            toks = tokenize(docs[pid])
            self.tf[pid] = Counter(toks)
            self.dl[pid] = len(toks)
            df.update(self.tf[pid].keys())
        n = len(self.ids)
        self.avgdl = (sum(self.dl.values()) / n) if n else 0.0
        # Lucene-style idf, always positive.
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def score(self, q_tokens: list[str], pid: str) -> float:
        tf, dl = self.tf[pid], self.dl[pid]
        s = 0.0
        for t in q_tokens:
            f = tf.get(t, 0)
            if f:
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / denom
        return s

    def rank(self, query: str) -> list[tuple[float, str]]:
        """All docs with score > 0, sorted by score desc then id asc."""
        q = tokenize(query)
        scored = [(-round(self.score(q, pid), 9), pid) for pid in self.ids]
        return [(-ns, pid) for ns, pid in sorted(scored) if ns < 0]


class ToolError(Exception):
    """Raised for bad tool input; returned to the agent as an is_error tool_result."""


class MockSearch:
    def __init__(self, corpus_path: str | Path, ranking: str = "bm25"):
        self.tool_defs = tool_defs(ranking)   # validates the ranking name
        self.ranking = ranking
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

        # BM25 index over searchable papers only (hidden papers are never returned).
        self._index = BM25({
            pid: f"{p.get('title', '')} {p.get('abstract', '')}"
            for pid, p in self.papers.items()
            if not p.get("hidden_from_search", False)
        })

        # Matches any corpus id as a whole token, e.g. "[W123]", "W123,", "T005-T010".
        alts = "|".join(re.escape(i) for i in sorted(self.papers, key=len, reverse=True))
        self._id_re = re.compile(rf"(?<![A-Za-z0-9_])(?:{alts})(?![A-Za-z0-9_])") if alts else None

    def rank(self, query: str) -> list[tuple[float, str]]:
        """Searchable papers matching the query, best first (ties by id)."""
        ranked = self._index.rank(query)
        if self.ranking == "bm25_citations":
            boosted = sorted(
                (-round(s * (1 + CITATION_BOOST * math.log1p(len(self._cites[pid]))), 9), pid)
                for s, pid in ranked
            )
            ranked = [(-ns, pid) for ns, pid in boosted]
        return ranked

    def find_ids(self, text: str) -> list[str]:
        """Corpus ids mentioned in text, unique, in order of first mention."""
        if not text or self._id_re is None:
            return []
        return list(dict.fromkeys(self._id_re.findall(text)))

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

        ranked = [
            (score, pid) for score, pid in self.rank(query)
            if year_from is None or (self.papers[pid].get("year") or 0) >= year_from
        ]

        results = []
        for _score, pid in ranked[:limit]:
            p = self.papers[pid]
            abstract = p.get("abstract", "") or ""
            snippet = abstract[:SNIPPET_CHARS] + ("..." if len(abstract) > SNIPPET_CHARS else "")
            # NOTE: status is never returned by any tool (see module docstring).
            results.append(
                {
                    "id": pid,
                    "title": p.get("title"),
                    "year": p.get("year"),
                    "venue": p.get("venue"),
                    "snippet": snippet,
                }
            )
        return {"query": query, "total_matches": len(ranked), "results": results}

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
