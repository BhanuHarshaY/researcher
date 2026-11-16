"""Dev-time corpus builder. Not used at run time (run time search is mocked).

Builds cases/<case>/corpus/papers.jsonl and SOURCES.md from a JSON spec:
  OpenAlex   metadata, retraction flag, type, venue, authors, references
  PubMed     structured abstracts (labelled sections become passages)
  Crossref   preprints that OpenAlex has merged into their journal versions,
             and retraction / withdrawal notices (linked with `updates:`)

Status is not stored on what the agent sees (see harness/tools/mock_search.py):
each retracted paper gets its real notice as a separate record that cites it,
and a superseded preprint is a separate record from its journal version.

Optional spec fields:
  "hidden_from_search": ["<curated label>", ...]
      those papers get hidden_from_search: true (reachable only through
      get_references / get_citations). The build fails if a label does not
      resolve or no searchable paper references the hidden one.
  "abstract_fallback": "semanticscholar"
      curated papers with no abstract in OpenAlex or PubMed (for example
      Elsevier journal articles) get theirs from one batched Semantic Scholar
      request. The response is frozen in <corpus>/s2_abstracts.json and reused,
      so reruns make no request. Truncated snippets ("...") are not used.

Standard library only. Run on the host from the repo root (cases/ is mounted
read-only inside the container):

  python3 -m corpus_tools.snapshot cases/case1_systematic_review/corpus/snapshot.json
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

OPENALEX = "https://api.openalex.org"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CROSSREF = "https://api.crossref.org"
S2_BATCH = "https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,abstract,externalIds"
UA = "litreview-testcases-snapshot/0.2 (academic test corpus builder)"
SELECT = ("id,doi,title,publication_year,publication_date,type,is_retracted,primary_location,"
          "authorships,abstract_inverted_index,referenced_works,ids,cited_by_count")
MAX_AUTHORS = 12
MAX_HOP = 10  # hard cap: references and citing papers taken per gold paper
NOTICE_RE = re.compile(r"^\s*(this (article|paper|preprint) (has been|was) (retracted|withdrawn)[^.]*\.)",
                       re.I)

NOTICE_TITLE_RE = re.compile(r"^(expression of concern|retraction( notice)?|notice of retraction|correction|"
                             r"erratum|corrigendum)\b", re.I)

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(__file__).resolve().parent / ".cache"   # gitignored; delete it to re-download


def _settings() -> dict:
    """CONTACT_EMAIL, OPENALEX_API_KEY, NCBI_API_KEY from the environment or the repo's .env.

    The email is sent as OpenAlex/Crossref `mailto` and NCBI `email` (their
    "polite" pools); the keys raise rate limits. All optional. Values are never
    printed, logged or used in cache keys.
    """
    vals = {}
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("CONTACT_EMAIL", "OPENALEX_API_KEY", "NCBI_API_KEY"):
        if os.environ.get(k):
            vals[k] = os.environ[k]
    return {k: vals.get(k) or None for k in ("CONTACT_EMAIL", "OPENALEX_API_KEY", "NCBI_API_KEY")}


SETTINGS = _settings()


def _with_contact(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc
    extra = {}
    if host == "api.openalex.org":
        extra = {"mailto": SETTINGS["CONTACT_EMAIL"], "api_key": SETTINGS["OPENALEX_API_KEY"]}
    elif host == "eutils.ncbi.nlm.nih.gov":
        extra = {"email": SETTINGS["CONTACT_EMAIL"], "api_key": SETTINGS["NCBI_API_KEY"]}
    elif host == "api.crossref.org":
        extra = {"mailto": SETTINGS["CONTACT_EMAIL"]}
    extra = {k: v for k, v in extra.items() if v}
    if not extra:
        return url
    return url + ("&" if "?" in url else "?") + urllib.parse.urlencode(extra)


def _min_gap(host: str) -> float:
    if host == "api.openalex.org":
        return 0.12 if SETTINGS["OPENALEX_API_KEY"] else 0.25
    if host == "eutils.ncbi.nlm.nih.gov":
        return 0.11 if SETTINGS["NCBI_API_KEY"] else 0.4
    if host == "api.crossref.org":
        return 0.3 if SETTINGS["CONTACT_EMAIL"] else 1.0
    return 0.5


class Progress:
    """Counts requests; every 25 prints elapsed time and an estimate of time left."""

    def __init__(self):
        self.n = self.cached = 0
        self.planned = 0
        self.phase = ""
        self.t0 = time.monotonic()

    def tick(self, cached: bool) -> None:
        self.n += 1
        self.cached += cached
        if self.n % 25 == 0:
            elapsed = time.monotonic() - self.t0
            left = max(self.planned - self.n, 0) * elapsed / self.n
            print(f"  [{self.n} requests, {self.cached} from cache | {self.phase} | {elapsed:.0f}s elapsed, "
                  f"about {left:.0f}s left of ~{self.planned} planned]", file=sys.stderr, flush=True)


PROGRESS = Progress()
_last_call: dict[str, float] = {}


def _get(url: str, tries: int = 7) -> bytes:
    """GET with an on-disk cache (keyed by the URL without contact/key params) and polite pacing."""
    key = hashlib.sha256(url.encode()).hexdigest()
    path = CACHE_DIR / key[:2] / key
    if path.exists():
        PROGRESS.tick(cached=True)
        return path.read_bytes()
    host = urllib.parse.urlparse(url).netloc
    for attempt in range(tries):
        wait = _last_call.get(host, 0.0) + _min_gap(host) - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.monotonic()
        req = urllib.request.Request(_with_contact(url), headers={"User-Agent": UA})
        backoff = 2 ** attempt
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            PROGRESS.tick(cached=False)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404 or attempt == tries - 1:
                raise
            if e.code == 429:  # rate limited: honour Retry-After (capped), else back off harder
                backoff = min(60.0, max(float(e.headers.get("Retry-After") or 0), 5 * (attempt + 1)))
                print(f"  rate limited by {host}; waiting {backoff:.0f}s", file=sys.stderr, flush=True)
        except urllib.error.URLError:
            if attempt == tries - 1:
                raise
        time.sleep(backoff)
    raise RuntimeError("unreachable")


def get_json(url: str) -> dict:
    return json.loads(_get(url))


# ------------------------------------------------------------------ OpenAlex
def short_id(openalex_url: str) -> str:
    return openalex_url.rsplit("/", 1)[-1]


def norm_doi(doi: str | None) -> str:
    return (doi or "").replace("https://doi.org/", "").strip().lower()


def oa_by_doi(doi: str) -> dict | None:
    try:
        return get_json(f"{OPENALEX}/works/doi:{urllib.parse.quote(doi, safe='/')}?select={SELECT}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def oa_list(params: dict) -> list[dict]:
    params = {**params, "select": SELECT}
    return get_json(f"{OPENALEX}/works?{urllib.parse.urlencode(params)}")["results"]


def oa_by_dois(dois: list[str]) -> dict[str, dict]:
    """Resolve many DOIs: 50 per request; single lookups only for DOIs the batch misses
    (for example a preprint DOI that OpenAlex has merged into its journal version)."""
    out: dict[str, dict] = {}
    batchable = [d for d in dict.fromkeys(dois) if "," not in d and "|" not in d]
    for i in range(0, len(batchable), 50):
        chunk = batchable[i:i + 50]
        for w in oa_list({"filter": "doi:" + "|".join(f"https://doi.org/{d}" for d in chunk), "per-page": 50}):
            out[norm_doi(w.get("doi"))] = w
    for d in dict.fromkeys(dois):
        if norm_doi(d) not in out:
            w = oa_by_doi(d)
            if w is not None:
                out[norm_doi(d)] = w
    return out


def oa_by_ids(ids: list[str]) -> dict[str, dict]:
    out = {}
    ids = list(dict.fromkeys(ids))
    for i in range(0, len(ids), 50):
        for w in oa_list({"filter": "openalex_id:" + "|".join(ids[i:i + 50]), "per-page": 50}):
            out[short_id(w["id"])] = w
    return out


def oa_by_title(title: str) -> dict | None:
    res = oa_list({"search": title, "per-page": 5})
    key = re.sub(r"[^a-z0-9]", "", title.lower())
    for w in res:
        if re.sub(r"[^a-z0-9]", "", (w.get("title") or "").lower()).startswith(key[:60]):
            return w
    return None


def date_filter(spec: dict) -> str:
    return f"from_publication_date:{spec['date_from']},to_publication_date:{spec['date_to']}"


def abstract_from_inverted(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


# ------------------------------------------------------------------ PubMed / Crossref
def pubmed_sections(pmids: list[str]) -> dict[str, list[tuple[str, str]]]:
    """Structured abstracts, 100 PMIDs per efetch request."""
    out: dict[str, list[tuple[str, str]]] = {}
    for i in range(0, len(pmids), 100):
        q = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(pmids[i:i + 100]), "retmode": "xml",
                                    "tool": "litreview-testcases-snapshot"})
        root = ET.fromstring(_get(f"{EUTILS}/efetch.fcgi?{q}"))
        for art in root.iter("PubmedArticle"):
            pmid = art.findtext(".//MedlineCitation/PMID")
            secs = []
            for at in art.iter("AbstractText"):
                text = " ".join("".join(at.itertext()).split())
                if text:
                    secs.append(((at.get("Label") or "").strip(), text))
            if pmid and secs:
                out[pmid] = secs
    return out


def crossref_works(dois: list[str]) -> dict[str, dict]:
    """Crossref records for many DOIs (filter=doi:a,doi:b is an OR), 20 per request."""
    out: dict[str, dict] = {}
    dois = list(dict.fromkeys(dois))
    for i in range(0, len(dois), 20):
        chunk = dois[i:i + 20]
        q = urllib.parse.urlencode({"filter": ",".join(f"doi:{d}" for d in chunk), "rows": len(chunk)})
        for it in get_json(f"{CROSSREF}/works?{q}")["message"]["items"]:
            out[norm_doi(it["DOI"])] = it
    return out


def crossref_notices(dois: list[str]) -> dict[str, list[dict]]:
    """Retraction / withdrawal notices that update each DOI (filter=updates:a,updates:b), 20 per request."""
    out: dict[str, list[dict]] = {norm_doi(d): [] for d in dois}
    dois = list(dict.fromkeys(dois))
    for i in range(0, len(dois), 20):
        chunk = dois[i:i + 20]
        q = urllib.parse.urlencode({"filter": ",".join(f"updates:{d}" for d in chunk), "rows": 100})
        for it in get_json(f"{CROSSREF}/works?{q}")["message"]["items"]:
            for u in it.get("update-to", []):
                target = norm_doi(u.get("DOI"))
                if (target in out and norm_doi(it["DOI"]) != target
                        and u.get("type") in ("retraction", "withdrawal", "removal")
                        and all(norm_doi(x["DOI"]) != norm_doi(it["DOI"]) for x in out[target])):
                    out[target].append(it)
    return out


def s2_abstracts(dois: list[str], frozen_path: Path) -> dict[str, dict]:
    """DOI -> {title, abstract} from Semantic Scholar. The frozen file is used first; DOIs
    not in it are fetched in batched POSTs (500 per request) and added to it. No contact
    details are sent (Semantic Scholar does not ask for them)."""
    frozen = json.loads(frozen_path.read_text()) if frozen_path.exists() else {}
    missing = [d for d in dict.fromkeys(dois) if d not in frozen]
    for i in range(0, len(missing), 500):
        chunk = missing[i:i + 500]
        print(f"Semantic Scholar: 1 batched request for {len(chunk)} DOIs", file=sys.stderr, flush=True)
        req = urllib.request.Request(S2_BATCH, data=json.dumps({"ids": [f"DOI:{d}" for d in chunk]}).encode(),
                                     method="POST", headers={"Content-Type": "application/json", "User-Agent": UA})
        for wait in (5, 10, 20, 30, None):  # the shared unauthenticated pool often answers 429
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    out = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or wait is None:
                    raise
                print(f"  Semantic Scholar rate limit (429); retrying in {wait}s", file=sys.stderr, flush=True)
                time.sleep(wait)
        for d, item in zip(chunk, out):
            frozen[d] = {"title": (item or {}).get("title"), "abstract": (item or {}).get("abstract")}
        frozen_path.write_text(json.dumps(dict(sorted(frozen.items())), indent=2, ensure_ascii=False) + "\n")
    return frozen


def s2_abstract_text(hit: dict | None) -> str:
    """Usable abstract text from a Semantic Scholar hit: leading 'Abstract' removed,
    empty for truncated snippets."""
    text = re.sub(r"^\s*abstract[:.\s]+", "", ((hit or {}).get("abstract") or "").strip(), flags=re.I)
    return "" if text.endswith(("...", "…")) else text


def strip_jats(s: str) -> str:
    s = re.sub(r"<jats:title>.*?</jats:title>", " ", s or "", flags=re.S)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


# ------------------------------------------------------------------ records
def clean_title(title: str, prefixes: list[str]) -> str:
    t = " ".join((title or "").split())
    for p in prefixes:
        if t.lower().startswith(p.lower()):
            t = t[len(p):].strip()
    return t


def split_passages(text: str, n_max: int = 3) -> list[str]:
    sents = [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text) if s.strip()]
    if len(sents) <= 1:
        return [text] if text else []
    n = min(n_max, max(2, len(sents) // 3))
    size = -(-len(sents) // n)
    return [" ".join(sents[i:i + size]) for i in range(0, len(sents), size)]


def make_passages(pid: str, sections: list[tuple[str, str]] | None, abstract: str) -> list[dict]:
    if sections and (len(sections) > 1 or sections[0][0]):
        items = [((label.title() if label else "Abstract"), text) for label, text in sections]
    else:
        items = [("Abstract", t) for t in split_passages(abstract)]
    return [{"pid": f"{pid}#p{i}", "section": sec, "text": t} for i, (sec, t) in enumerate(items, 1)]


def oa_record(w: dict, pm: dict, prefixes: list[str]) -> dict:
    pid = short_id(w["id"])
    pmid = re.sub(r"\D", "", (w.get("ids") or {}).get("pmid") or "")
    sections = pm.get(pmid)
    if sections:
        abstract = " ".join(f"{l}: {t}" if l else t for l, t in sections)
    else:
        abstract = abstract_from_inverted(w.get("abstract_inverted_index"))
    notice = None
    m = NOTICE_RE.match(abstract)
    if m:  # keep status out of search snippets; the notice stays visible via get_paper
        notice = m.group(1)
        abstract = abstract[m.end():].strip()
    src = (w.get("primary_location") or {}).get("source") or {}
    passages = make_passages(pid, sections if not notice else None, abstract)
    if notice:
        passages.append({"pid": f"{pid}#p{len(passages) + 1}", "section": "Notice", "text": notice})
    status = "retracted" if w.get("is_retracted") else ("preprint" if w.get("type") == "preprint" else "published")
    return {
        "id": pid,
        "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
        "title": clean_title(w.get("title"), prefixes),
        "abstract": abstract,
        "year": w.get("publication_year"),
        "date": w.get("publication_date"),
        "venue": src.get("display_name"),
        "authors": [a["author"]["display_name"] for a in (w.get("authorships") or [])[:MAX_AUTHORS]],
        "source": "pubmed" if sections else "openalex",
        "status": status,
        "published_version_id": None,
        "references": [short_id(r) for r in w.get("referenced_works") or []],
        "cited_by": [],
        "passages": passages,
        "hidden_from_search": False,
        "synthetic": False,
        "_type": w.get("type"),
        "_cited_by_count": w.get("cited_by_count"),
    }


def _cr_date(m: dict) -> tuple[int | None, str | None]:
    parts = (m.get("posted") or m.get("published") or m.get("issued") or {}).get("date-parts", [[None]])[0]
    if not parts or parts[0] is None:
        return None, None
    return parts[0], "-".join(f"{x:02d}" if i else str(x) for i, x in enumerate(parts))


def crossref_record(doi: str, published_id: str | None, prefixes: list[str], m: dict) -> dict:
    abstract = strip_jats(m.get("abstract", ""))
    year, d = _cr_date(m)
    venue = ((m.get("institution") or [{}])[0].get("name")) or (m.get("container-title") or [None])[0] \
        or m.get("publisher")
    authors = [" ".join(x for x in (a.get("given"), a.get("family")) if x) for a in m.get("author", [])]
    return {
        "id": doi,
        "doi": doi,
        "title": clean_title((m.get("title") or [""])[0], prefixes),
        "abstract": abstract,
        "year": year,
        "date": d,
        "venue": venue,
        "authors": authors[:MAX_AUTHORS],
        "source": "crossref",
        "status": "preprint",
        "published_version_id": published_id,
        "references": [],
        "cited_by": [],
        "passages": make_passages(doi, None, abstract),
        "hidden_from_search": False,
        "synthetic": False,
        "_type": "preprint",
        "_cited_by_count": None,
    }


def mentions(w: dict, word: str) -> bool:
    text = f"{w.get('title') or ''} {abstract_from_inverted(w.get('abstract_inverted_index'))}".lower()
    return word.lower() in text


# ------------------------------------------------------------------ build
def build(spec_path: Path) -> None:
    spec = json.loads(spec_path.read_text())
    corpus_dir = spec_path.parent
    prefixes = spec.get("strip_title_prefixes", [])
    excluded = [d.lower() for d in spec.get("exclude_doi_prefixes", [])]
    log: list[str] = []
    works: dict[str, dict] = {}      # openalex id -> work
    origin: dict[str, str] = {}      # openalex id -> why it is in the corpus
    resolved: dict[str, dict[str, str | None]] = {}

    def keep(w: dict, why: str, force: bool = False) -> bool:
        doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
        if any(doi.startswith(p) for p in excluded):
            return False
        wid = short_id(w["id"])
        if wid not in works:
            if not force and not w.get("abstract_inverted_index"):
                return False
            works[wid] = w
            origin[wid] = why
        return True

    hop = spec.get("one_hop") or {}
    refs_cap = min(hop.get("refs_per_gold", 0), MAX_HOP)
    citers_cap = min(hop.get("citers_per_gold", 0), MAX_HOP)
    all_curated = [v for g in spec["groups"].values() for v in g.values()]
    n_gold = len(spec["groups"].get("gold", {}))
    PROGRESS.planned = (-(-len(all_curated) // 50) + sum(v.startswith("title:") for v in all_curated)
                        + len(spec["seed_queries"]) + n_gold + -(-n_gold * 30 // 50)
                        + -(-spec.get("max_papers", 400) // 100) + 3)
    for host in ("api.openalex.org", "eutils.ncbi.nlm.nih.gov", "api.crossref.org"):
        sent = urllib.parse.parse_qs(urllib.parse.urlparse(_with_contact(f"https://{host}/x?a=1")).query)
        names = sorted(k for k in sent if k != "a")
        print(f"contact params sent to {host}: {', '.join(names) or 'none'}", file=sys.stderr, flush=True)
    print(f"plan: about {PROGRESS.planned} requests (cached responses are reused); target about "
          f"{spec.get('target_papers', '?')} papers, max {spec.get('max_papers', 400)}", file=sys.stderr, flush=True)

    # 1. Curated groups resolved by DOI, 50 per request (always kept).
    PROGRESS.phase = "curated DOIs"
    by_doi = oa_by_dois([v for v in all_curated if not v.startswith("title:")])
    for group, items in spec["groups"].items():
        resolved[group] = {}
        for label, doi in items.items():
            w = oa_by_title(doi[len("title:"):]) if doi.startswith("title:") else by_doi.get(norm_doi(doi))
            if w is None:
                resolved[group][label] = None
                log.append(f"- NOT FOUND in OpenAlex: {group} / {label} ({doi})")
                continue
            keep(w, f"{group}: {label}", force=True)
            resolved[group][label] = short_id(w["id"])
    print(f"curated: {len(works)} works", file=sys.stderr, flush=True)

    # 2. Seed queries within the date window.
    PROGRESS.phase = "seed queries"
    seed_counts = []
    for sq in spec["seed_queries"]:
        res = oa_list({"search": sq["query"], "filter": date_filter(spec), "per-page": sq["n"]})
        added = sum(keep(w, f"seed: {sq['query']}") and origin[short_id(w['id'])] == f"seed: {sq['query']}"
                    for w in res)
        seed_counts.append((sq["query"], len(res), added))
    print(f"after seeds: {len(works)} works", file=sys.stderr, flush=True)

    # 3. One hop from gold: at most MAX_HOP references and MAX_HOP citing papers per
    #    gold paper, both about the topic. All references are fetched in batches of 50.
    PROGRESS.phase = "citation hop"
    hop_added = 0
    gold_ids = [g for g in (resolved.get("gold") or {}).values() if g]
    ref_lists = {g: [short_id(r) for r in works[g].get("referenced_works") or []] for g in gold_ids}
    ref_works = oa_by_ids([r for refs in ref_lists.values() for r in refs])
    for label, gid in (resolved.get("gold") or {}).items():
        if not gid:
            continue
        refs = [ref_works[r] for r in ref_lists[gid] if r in ref_works and mentions(ref_works[r], hop.get("keyword", ""))]
        for w in refs[:refs_cap]:
            hop_added += keep(w, f"reference of {label}") and origin[short_id(w['id'])] == f"reference of {label}"
        if citers_cap:
            citers = oa_list({"filter": f"cites:{gid},{date_filter(spec)}", "search": hop.get("keyword", ""),
                              "per-page": citers_cap})
            for w in citers[:citers_cap]:
                hop_added += keep(w, f"cites {label}") and origin[short_id(w['id'])] == f"cites {label}"
    print(f"after one hop: {len(works)} works", file=sys.stderr, flush=True)

    # 4. Cap size: curated first, then seeds and hop in insertion order. Room is kept
    #    for the Crossref preprint and notice records added later, so the final
    #    corpus stays within max_papers.
    cap = spec.get("max_papers", 400) - len(spec.get("crossref_preprints", [])) - 10
    if len(works) > cap:
        curated = [k for k, v in origin.items() if not v.startswith(("seed:", "reference of", "cites "))]
        rest = [k for k in works if k not in curated]
        for k in rest[cap - len(curated):]:
            works.pop(k)
            origin.pop(k)

    # 5. Drop notices (expressions of concern, retraction/correction notices) and
    #    duplicate versions of the same work (same normalised title; curated wins).
    curated_ids = {k for k, v in origin.items() if not v.startswith(("seed:", "reference of", "cites "))}
    seen_titles: dict[str, str] = {}
    for wid in sorted(works, key=lambda k: (k not in curated_ids, list(works).index(k))):
        title = clean_title(works[wid].get("title"), prefixes)
        if NOTICE_TITLE_RE.match(title) and wid not in curated_ids:
            log.append(f"- dropped notice record {wid}: {title[:80]}")
            works.pop(wid); origin.pop(wid)
            continue
        key = re.sub(r"[^a-z0-9]", "", title.lower())
        if key in seen_titles and wid not in curated_ids:
            log.append(f"- dropped duplicate {wid} (same title as {seen_titles[key]}): {title[:70]}")
            works.pop(wid); origin.pop(wid)
            continue
        seen_titles.setdefault(key, wid)

    # 6. PubMed structured abstracts, then records.
    pmids = sorted({re.sub(r"\D", "", (w.get("ids") or {}).get("pmid") or "") for w in works.values()} - {""})
    print(f"fetching {len(pmids)} PubMed abstracts (100 per request)...", file=sys.stderr, flush=True)
    PROGRESS.phase = "PubMed abstracts"
    pm = pubmed_sections(pmids)
    records = {wid: oa_record(w, pm, prefixes) for wid, w in works.items()}

    # 7. Crossref preprints superseded by a curated journal version.
    resolved["crossref_preprints"] = {}
    PROGRESS.phase = "Crossref preprints"
    cr = crossref_works([item["doi"] for item in spec.get("crossref_preprints", [])])
    for item in spec.get("crossref_preprints", []):
        pub_id = None
        for group in resolved.values():
            pub_id = pub_id or group.get(item["published_label"])
        if not pub_id or norm_doi(item["doi"]) not in cr:
            log.append(f"- SKIPPED preprint {item['label']}: published version or Crossref record not found")
            continue
        rec = crossref_record(item["doi"], pub_id, prefixes, cr[norm_doi(item["doi"])])
        records[rec["id"]] = rec
        origin[rec["id"]] = f"crossref_preprints: {item['label']}"
        resolved["crossref_preprints"][item["label"]] = rec["id"]

    # 7b. OpenAlex preprint records superseded by a curated journal version
    #     (OpenAlex keeps some preprints separate, e.g. Research Square).
    resolved["openalex_preprints"] = {}
    links = spec.get("openalex_preprint_links", [])
    by_link = oa_by_dois([x["doi"] for x in links]) if links else {}
    for item in links:
        w = by_link.get(norm_doi(item["doi"]))
        pub_id = next((g.get(item["published_label"]) for g in resolved.values() if g.get(item["published_label"])), None)
        if not w or not pub_id:
            log.append(f"- SKIPPED preprint link {item['label']}: preprint or published version not found")
            continue
        pid = short_id(w["id"])
        if pid not in records:
            records[pid] = oa_record(w, pm, prefixes)
            origin[pid] = f"openalex_preprint_links: {item['label']}"
        records[pid].update(status="preprint", published_version_id=pub_id)
        resolved["openalex_preprints"][item["label"]] = pid

    # 8. Retraction / withdrawal notices: one real notice record per retracted
    #    paper, citing it (so it shows up in search and in get_citations).
    print("looking up retraction notices in Crossref (one batched request)...", file=sys.stderr, flush=True)
    PROGRESS.phase = "Crossref notices"
    resolved["retraction_notices"] = {}
    notice_dois: set[str] = set()
    retracted = sorted(k for k, r in records.items() if r["status"] == "retracted")
    all_notices = crossref_notices([records[k]["doi"] for k in retracted if records[k]["doi"]])
    for pid in retracted:
        if pid not in records:
            continue  # dropped below as the notice of another paper
        doi = records[pid]["doi"]
        if not doi:
            log.append(f"- no DOI for retracted {pid}; no notice looked up")
            continue
        notices = all_notices.get(norm_doi(doi), [])
        if not notices:
            log.append(f"- no Crossref notice found for retracted {pid} ({doi})")
        for m in notices[:1]:
            notice_dois.add(m["DOI"].lower())
            # OpenAlex sometimes indexes the notice itself as a (retracted) work: drop that copy.
            for k in [k for k, r in records.items() if (r.get("doi") or "").lower() == m["DOI"].lower()]:
                log.append(f"- dropped {k}: it is the retraction notice {m['DOI']}, re-added from Crossref")
                records.pop(k)
                origin.pop(k, None)
            rec = crossref_record(m["DOI"], None, [], m=m)
            rec.update(status="published", references=[pid], notice_for=pid, source="crossref")
            if not rec["abstract"]:
                rec["passages"] = []
            records[rec["id"]] = rec
            origin[rec["id"]] = f"notice for {pid}"
            resolved["retraction_notices"][records[pid]["title"][:60]] = rec["id"]

    # 9. Keep references inside the corpus; write files.
    for r in records.values():
        r["references"] = sorted(x for x in r["references"] if x in records and x != r["id"])
    for r in records.values():
        for ref in r["references"]:
            records[ref]["cited_by"].append(r["id"])
    for r in records.values():
        r["cited_by"] = sorted(set(r["cited_by"]))

    # 10. Optional: abstract fallback for curated papers, then papers hidden from search.
    notes: list[str] = []
    curated = [pid for g in spec["groups"] for pid in (resolved.get(g) or {}).values() if pid in records]
    if spec.get("abstract_fallback") == "semanticscholar":
        need = sorted(pid for pid in set(curated) if not records[pid]["abstract"] and records[pid]["doi"])
        frozen = corpus_dir / "s2_abstracts.json"
        s2 = s2_abstracts([records[pid]["doi"].lower() for pid in need], frozen) if need else {}
        for pid in need:
            r = records[pid]
            hit = s2.get(r["doi"].lower())
            text = s2_abstract_text(hit)
            if not text:
                why = "only a truncated snippet" if (hit or {}).get("abstract") else "no abstract"
                notes.append(f"- {pid} ({r['title'][:60]}): {why} in Semantic Scholar; kept without passages")
                continue
            r["abstract"] = text
            r["passages"] = make_passages(pid, None, text)
            notes.append(f"- {pid} ({r['title'][:60]}): abstract from Semantic Scholar (frozen in {frozen.name})")
    elif spec.get("abstract_fallback"):
        sys.exit(f"unknown abstract_fallback {spec['abstract_fallback']!r} (expected 'semanticscholar')")
    for label in spec.get("hidden_from_search", []):
        pid = next((g.get(label) for g in resolved.values() if g.get(label)), None)
        if not pid or pid not in records:
            sys.exit(f"hidden_from_search: {label!r} is not a resolved curated paper in the corpus")
        records[pid]["hidden_from_search"] = True
    for label in spec.get("hidden_from_search", []):
        pid = next(g.get(label) for g in resolved.values() if g.get(label))
        reach = sorted(k for k, r in records.items() if pid in r["references"] and not r["hidden_from_search"])
        if not reach:
            sys.exit(f"hidden_from_search: {label} ({pid}) is referenced by no searchable paper (unreachable)")
        notes.append(f"- {pid} ({label}) hidden from keyword search; referenced by {len(reach)} searchable "
                     f"papers, e.g. {', '.join(reach[:6])}")

    meta ={k: {"type": r.pop("_type"), "cited_by_count": r.pop("_cited_by_count")} for k, r in records.items()}
    out = corpus_dir / "papers.jsonl"
    with open(out, "w") as f:
        for k in sorted(records):
            f.write(json.dumps(records[k], ensure_ascii=False) + "\n")
    (corpus_dir / "resolved_ids.json").write_text(json.dumps(resolved, indent=2, ensure_ascii=False) + "\n")
    if len(records) > spec.get("max_papers", 400):
        log.append(f"- WARNING: {len(records)} papers exceeds max_papers {spec.get('max_papers')}")
    write_sources(corpus_dir, spec, records, meta, origin, resolved, seed_counts, hop_added, log, notes)
    print(f"wrote {out} ({len(records)} papers) after {PROGRESS.n} requests "
          f"({PROGRESS.cached} from cache) in {time.monotonic() - PROGRESS.t0:.0f}s", file=sys.stderr)


def write_sources(corpus_dir, spec, records, meta, origin, resolved, seed_counts, hop_added, log, notes=None):
    by_status = {}
    for r in records.values():
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    lines = [
        f"# Corpus sources: {spec['case']}",
        "",
        f"Built {date.today().isoformat()} with `python3 -m corpus_tools.snapshot {corpus_dir}/snapshot.json`.",
        f"Frozen after that: run-time search never calls these services.",
        "",
        "Sources: OpenAlex (metadata, retraction flags, references), PubMed E-utilities (structured "
        "abstracts as passages), Crossref (preprints that OpenAlex merges into journal versions).",
        "",
        f"- Papers: **{len(records)}** ({', '.join(f'{k}: {v}' for k, v in sorted(by_status.items()))})",
        f"- Passages from PubMed structured abstracts: {sum(r['source'] == 'pubmed' for r in records.values())}",
        f"- Seed/hop date window: {spec['date_from']} to {spec['date_to']} (curated papers are kept regardless)",
        f"- Title prefixes stripped (status is shown only by get_paper): {', '.join(spec.get('strip_title_prefixes', []))}",
        f"- Excluded DOI prefixes: {', '.join(spec.get('exclude_doi_prefixes', [])) or 'none'}",
        "",
        "## Seed queries (OpenAlex relevance order)",
        "",
        "| Query | Returned | New papers |",
        "|---|---|---|",
    ]
    lines += [f"| {q} | {n} | {a} |" for q, n, a in seed_counts]
    lines += ["", f"One hop from gold (references and citing papers mentioning "
                  f"'{(spec.get('one_hop') or {}).get('keyword', '')}'): {hop_added} new papers.", ""]
    for group, items in resolved.items():
        lines += [f"## {group}", "", "| Label | Corpus id | Status | Title |", "|---|---|---|---|"]
        for label, pid in items.items():
            r = records.get(pid) if pid else None
            lines.append(f"| {label} | {pid or 'NOT FOUND'} | {r['status'] if r else ''} | "
                         f"{(r['title'][:90] if r else '')} |")
        lines.append("")
    if notes:
        lines += ["## Abstract fallback and hidden papers", "",
                  "Abstracts that OpenAlex and PubMed lack come from Semantic Scholar (spec "
                  "`abstract_fallback`); papers in spec `hidden_from_search` are reachable only "
                  "through citation links.", ""] + notes + [""]
    if log:
        lines += ["## Dropped records and problems", ""] + log + [""]
    (corpus_dir / "SOURCES.md").write_text("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    build(Path(sys.argv[1]))
