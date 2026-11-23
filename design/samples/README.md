# Sample input files

These are fixtures for building the proposed agent's modules in parallel
(DESIGN.md §3.7). Each one follows the contracts in DESIGN.md §3.2–3.3.

| File | Module (owner) | Shows |
|---|---|---|
| `retrieval_input.json` | Retrieval (Bhanu) | Approved queries, the budget split, citation-chasing and status settings |
| `screening_input.json` → `screening_output.json` | Screening (Vishwani) | One batch at snippet and title level: an include, two excludes (population, design) and a title-only `unsure` |
| `steering_input.json` → `steering_output.json` | Steering (Bhanu) | A criteria change that only narrows: the re-screen set, kept / dropped / unsure papers, carried decisions, no re-search |
| `synthesis_input.json` → `claim_check_output.json` | Synthesis (Bhanu), claim checker (Vishwani) | An approved set, an outline, linked passages and a confusable preprint; one supported claim and one misattributed claim |
| `gate_messages.json`, `gate_plan.txt`, `gate_paper_set.txt` | Interface (Wendi), sim gate rules (Vishwani) | A plan gate and a paper-set gate with full items, coverage and budget; their text renderings; sim and human responses |
| `log_excerpt.jsonl` | Log (Bhanu) | Query, decision, gate-response and budget entries |

How these were made:
- **Ids.** Every id comes from the synthetic `_toy` case
  (`cases/_toy/corpus/papers.jsonl`), never from the three test cases.
- **Text.** Titles, snippets (the first 300 characters of the abstract),
  passages and quotes are verbatim from the toy corpus. Each quote appears in
  the text seen at its stated basis.
- **Search results.** The result lists for Q1–Q3 are the real output of
  `harness/tools/mock_search.py` on the toy corpus.
- **Gate text.** The `text` field of each gate in `gate_messages.json` is
  identical to its `.txt` file.
- **T007** is retracted in the toy corpus. Its notice is only in its full
  record, which this sample run never opened, so the paper-set gate shows it as
  `sweep only` rather than claiming it was checked. This is the intended,
  honest behaviour.

Once `harness/contracts/` exists, a unit test will validate each file against
its JSON Schema and re-check every quote against the toy corpus.
