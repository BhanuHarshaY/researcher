# Changes case 2 needed outside its folder (all applied 2026-11-16)

| Change | Where | Status |
|---|---|---|
| Spec field `hidden_from_search` (list of curated labels). The build fails if a label doesn't resolve or if no searchable paper references the hidden one. | `corpus_tools/snapshot.py` | applied |
| validate checks that every hidden paper is referenced by at least one searchable paper, and prints the count | `corpus_tools/validate.py` | applied |
| Every claim citing a `pairs` paper is judged (no cap since v2; those outside the sample get a second judge call) and counts toward `bd_misattribution`; pair papers come first in the judge's context; `judgments.json` lists them under `pair_claims` | `harness/metrics/core.py`, `score.py` | applied |
| v2: a "misattributed" label without a valid `correct_id` gets one re-judge, then counts as unsupported; claims citing title-only records are marked `weak_check`; optional `observe_key_papers_at_turn` observation | `harness/metrics/core.py`, `score.py`, `judge.py` | applied |
| A preprint and its journal version (`report_of`) are the same paper, so "misattributed" to another version counts as supported | `harness/metrics/core.py`, `score.py` | applied |
| Spec option `abstract_fallback: "semanticscholar"`, frozen in `corpus/s2_abstracts.json` | `corpus_tools/snapshot.py` | applied |
| Per-case `search_ranking: bm25 \| bm25_citations` (default `bm25`), recorded in `config.json`. Case 2 uses `bm25_citations`. | `harness/tools/mock_search.py`, `run.py`, `score.py`, `agents/baseline.py` | applied (replaces the author-name search idea) |

Also applied:
- case 2's `build/postprocess.py` was retired;
- `shared/metrics.md` documents pair claims, the version rule and the search ranking;
- unit tests cover each change.

Case 1 was checked to be unchanged in four ways:
- its corpus build;
- its tool definitions;
- all 409 re-run tool outputs from its 5 runs;
- its judge inputs, `judgments.json` and `reward.json`, from replaying the stored judge answers.

CLAUDE.md now documents `search_ranking` and `pairs` in its `config.json` and `case.yaml` sections.
