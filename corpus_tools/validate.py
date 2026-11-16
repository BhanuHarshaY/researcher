"""Check a case's case.yaml against its frozen corpus. Free (no API calls).

  docker compose run --rm harness python -m corpus_tools.validate case1_systematic_review

Fails (exit 1) on any problem:
- every id in gold/key/relevant/off_scope/traps/post_change lists exists in the corpus
- key is a subset of gold, gold is a subset of relevant; lists are disjoint where they must be
- gold papers are searchable unless the case says otherwise (hidden ones are reported)
- every hidden paper stays reachable: at least one searchable paper references it
- search_ranking is a known ranking; every id in `pairs` is in the corpus and relevant
- superseded-preprint traps point to a published version that is in the corpus
- agent-visible fields carry no synthetic markers ("toy", "placeholder", fake DOI
  prefixes, status prefixes such as "RETRACTED:" in titles)
- the sim-user script templates render
- id lists match corpus/labels.json when that file exists
"""
from __future__ import annotations

import json
import re
import sys

import yaml

from harness.config import CASES_DIR
from harness.tools.mock_search import INTERNAL_FIELDS, MockSearch
from harness.users.sim_user import render_template

MARKER_RE = re.compile(r"\btoy\b|placeholder|10\.0000/|^(retracted|withdrawn)\b|\bsynthetic record\b", re.I)


def validate(case_name: str) -> list[str]:
    d = CASES_DIR / case_name
    case = yaml.safe_load((d / "case.yaml").read_text())
    errs: list[str] = []
    ranking = case.get("search_ranking", "bm25")
    try:
        s = MockSearch(d / "corpus" / "papers.jsonl", ranking=ranking)
    except ValueError as e:
        errs.append(str(e))
        s = MockSearch(d / "corpus" / "papers.jsonl")
    ids = set(s.papers)
    lists = {k: list(case.get(k) or []) for k in
             ("gold_ids", "key_ids", "relevant_ids", "off_scope_ids", "post_change_expected_ids")}
    traps = case.get("traps") or []
    lists["trap_ids"] = [t["id"] for t in traps]

    for name, xs in lists.items():
        for x in xs:
            if x not in ids:
                errs.append(f"{name}: {x} is not in the corpus")
        if len(set(xs)) != len(xs):
            errs.append(f"{name}: duplicate ids")
    if not set(lists["key_ids"]) <= set(lists["gold_ids"]):
        errs.append("key_ids must be a subset of gold_ids")
    near = [x["id"] if isinstance(x, dict) else x for x in case.get("near_miss_ids") or []]
    for x in near:
        if x not in ids:
            errs.append(f"near_miss_ids: {x} is not in the corpus")
    if not set(near) <= set(lists["off_scope_ids"]):
        errs.append("near_miss_ids must be a subset of off_scope_ids")
    if not set(lists["gold_ids"]) <= set(lists["relevant_ids"]):
        errs.append("gold_ids must be a subset of relevant_ids")
    for a, b in (("relevant_ids", "off_scope_ids"), ("relevant_ids", "trap_ids"), ("off_scope_ids", "trap_ids")):
        both = set(lists[a]) & set(lists[b])
        if both:
            errs.append(f"{a} and {b} overlap: {sorted(both)}")

    for t in traps:
        if t.get("kind") not in ("retracted", "superseded_preprint"):
            errs.append(f"trap {t['id']}: unknown kind {t.get('kind')}")
        p = s.papers.get(t["id"])
        if not p:
            continue
        if t.get("kind") == "retracted" and p.get("status") != "retracted":
            errs.append(f"trap {t['id']}: kind retracted but status is {p.get('status')}")
        if t.get("kind") == "superseded_preprint":
            if p.get("status") != "preprint" or p.get("published_version_id") not in ids:
                errs.append(f"trap {t['id']}: superseded preprint needs status preprint and a published version in the corpus")
        if bool(p.get("synthetic")) == bool(t.get("real")):
            errs.append(f"trap {t['id']}: 'real' does not match the record's 'synthetic' flag")

    hidden = [g for g in lists["gold_ids"] if s.papers.get(g, {}).get("hidden_from_search")]
    reach: dict[str, int] = {}
    for pid, p in s.papers.items():
        if p.get("hidden_from_search"):
            reach[pid] = sum(pid in q.get("references", []) and not q.get("hidden_from_search")
                             for q in s.papers.values())
            if not reach[pid]:
                errs.append(f"{pid}: hidden from search and referenced by no searchable paper (unreachable)")

    from harness.metrics.core import CASE_METRICS
    for name in case.get("case_metrics") or []:
        if name not in CASE_METRICS:
            errs.append(f"case_metrics: unknown metric {name!r} (known: {sorted(CASE_METRICS)})")
        elif (case.get("thresholds") or {}).get(name) is None:
            errs.append(f"case_metrics: {name} needs a threshold in thresholds")
        if name == "post_change_recall" and not lists["post_change_expected_ids"]:
            errs.append("case_metrics: post_change_recall needs post_change_expected_ids")

    obs_turn = case.get("observe_key_papers_at_turn")
    if obs_turn is not None and (not isinstance(obs_turn, int) or not 1 <= obs_turn <= 6):
        errs.append(f"observe_key_papers_at_turn must be a user turn from 1 to 6, not {obs_turn!r}")

    pairs = case.get("pairs") or []
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2 or pair[0] == pair[1]:
            errs.append(f"pairs: {pair} must be two different paper ids")
            continue
        for x in pair:
            if x not in ids:
                errs.append(f"pairs: {x} is not in the corpus")
            elif x not in set(lists["relevant_ids"]):
                errs.append(f"pairs: {x} is not in relevant_ids")
    for p in s.papers.values():
        visible = {k: v for k, v in p.items() if k not in INTERNAL_FIELDS}
        for field in ("id", "doi", "title", "venue"):
            # Retraction-notice records are meant to say "retracted"/"withdrawn": that is how status shows.
            if p.get("notice_for") and field == "title":
                continue
            if visible.get(field) and MARKER_RE.search(str(visible[field])):
                errs.append(f"{p['id']}: marker in {field}: {visible[field][:80]!r}")
        if "10.0000/" in json.dumps(visible):
            errs.append(f"{p['id']}: fake DOI prefix in record")

    for f in (case.get("script") or {}).get("followups") or []:
        try:
            render_template(f["message"], s.papers)
        except KeyError as e:
            errs.append(f"script after_turn {f.get('after_turn')}: {e}")

    report_of = case.get("report_of") or {}
    for rep, trial in report_of.items():
        if rep not in ids or trial not in ids:
            errs.append(f"report_of: {rep} -> {trial} not both in the corpus")
        elif trial not in set(lists["relevant_ids"]):
            errs.append(f"report_of: {rep} points to {trial}, which is not gold or relevant")

    labels = d / "corpus" / "labels.json"
    if labels.exists():
        L = json.loads(labels.read_text())
        for k in ("gold_ids", "key_ids", "relevant_ids", "off_scope_ids"):
            if k in L and sorted(L[k]) != sorted(lists[k]):
                errs.append(f"{k} in case.yaml differs from corpus/labels.json")

    print(f"{case_name}: {len(ids)} papers | gold {len(lists['gold_ids'])} (hidden {len(hidden)}) | "
          f"key {len(lists['key_ids'])} | relevant {len(lists['relevant_ids'])} | "
          f"off-scope {len(lists['off_scope_ids'])} (near-miss {len(near)}) | traps {len(traps)} | "
          f"status {dict(sorted({p['status']: 0 for p in s.papers.values()}.items()))}".replace(": 0", "")
          + f" | search {ranking} | pairs {len(pairs)}")
    for pid, n in reach.items():
        print(f"  hidden {pid}: referenced by {n} searchable paper(s)")
    return errs


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    problems = validate(sys.argv[1])
    for e in problems:
        print("ERROR:", e)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)
