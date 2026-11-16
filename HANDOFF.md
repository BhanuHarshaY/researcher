# Handoff 1: status and remaining work

Written Mon 16 Nov 2026, 18:15 EST, at tag `handoff-1`. **Deadline: tonight, 23:59.**
**Budget cap: stop and check with the team before any step that would take total spend past $60.**

## At a glance

| | Case 1 (systematic review) | Case 2 (related work) | Case 3 (field map) |
|---|---|---|---|
| Final runs | 5 of 5 | 5 of 5 | **0 of 5** |
| `summary.md` | done | done | not yet |
| Requested changes | n/a | done | v2 changes in `case.yaml`, **not yet piloted** |
| DOC.md (8 sections) | 0 complete, 2 partial | 0 complete, 3 partial | 0 complete, 2 partial |
| Scores up to date | reward yes; 2 runs need a free rescore of notes in `judgments.json` | yes | n/a |

Team files: `shared/metrics.md` complete, `shared/survey_interview.md` complete, **`README.md` missing**.
Spend so far: about **$34** ($30.93 recorded in the run files). Remaining paid work: about **$21**, which projects to about **$55**.

## Rules for teammates

1. **Don't change a case's design after its final runs.** For cases 1 and 2 (now), and for case 3 once its final runs start, these are frozen: `case.yaml` (including the script), `corpus/` (including `labels.json`), `persona.md`, `harness/agents/baseline_prompt.md` and `config/models.yaml`. Any change makes all 5 runs invalid. If you think something is wrong, write it down and tell the team; don't fix it in place.
2. **Only one person edits shared code** (`harness/`, `corpus_tools/`, `shared/`, `config/`, `tests/`, `Dockerfile`, `docker-compose.yml`). Shared-code owner tonight: `________` (fill in before anyone edits). Everyone else edits only case folders, `runs/` and docs.
3. **Ask before any paid step.** Paid means anything that runs `harness.run` or `harness.metrics.score`, since both call the Anthropic API. Post the command and its cost estimate (below) in the team chat and wait for an OK. Run free commands with `-e ANTHROPIC_API_KEY=`, which blanks the key inside the container, so they can't spend even by mistake.
4. **Never commit `.env`.** Run `git status` before every commit. Don't use `git add -A` or `git add .` in the repo root.
5. **Budget:** if a step would take the total past **$60**, stop and check with the team first. Add what you spend to the cost table below.
6. Commit messages and branch names follow [CONTRIBUTING.md](CONTRIBUTING.md). The full spec is [CLAUDE.md](CLAUDE.md); it is tracked as of this handoff.

## Set up from a fresh clone

```bash
git clone https://github.com/BhanuHarshaY/researcher.git
cd researcher
cp .env.example .env            # put ANTHROPIC_API_KEY in .env; never commit it
docker compose build

# Free checks (the key is blanked, so nothing can spend):
docker compose run --rm -e ANTHROPIC_API_KEY= harness python -m unittest discover -s tests -t .
for c in _toy case1_systematic_review case2_related_work case3_field_map; do
  docker compose run --rm -e ANTHROPIC_API_KEY= harness python -m corpus_tools.validate $c
done
```

Expected: `Ran 78 tests ... OK` and `OK` for each case. `harness.metrics.summarize` uses only the standard library, so it also runs on the host with `python3`.

## Status check (16 Nov, 18:10 EST)

### Repo health

- **Tests:** 78 pass, including the 2 added in this handoff.
- **Validate:** all four cases OK.
  - `_toy`: 10 papers.
  - case 1: 276 papers, 25 gold, 10 traps.
  - case 2: 256 papers, 17 gold (1 hidden, reachable from 42 papers), 3 pairs, 5 traps.
  - case 3: 286 papers, 33 gold, 0 traps.
- **Git before this handoff:** `main` was at `982ccbf`, one commit (case 3) ahead of `origin/main`. Uncommitted changes:
  - `.gitignore`: stopped ignoring `CLAUDE.md`, so the spec could be committed.
  - `CLAUDE.md`: untracked. The spec; no keys or emails in it.
  - `CONTRIBUTING.md`: new.
  - `runs/pilots/`: untracked. The case 2 v1 pilot (1 run) and the case 3 v1 pilots (2 runs and a summary). Both REJECTED.md files cite these folders.
  - **Shared code had no uncommitted changes.** The handoff adds two new files, `harness/metrics/replay.py` and `tests/test_replay.py`, and changes no existing code. All of the above is committed in the `handoff-1` commits.
- **Secrets and images:**
  - `.env` is not tracked. It is ignored at `.gitignore` line 1 and kept out of the Docker image by `.dockerignore`; the built image has no `/app/.env`.
  - No Docker images or archives are tracked. The largest tracked file is case 1's corpus, at 2.1 MB.
  - `AGENTS.md` stays gitignored. It is an old copy of the spec with wrong model names, so don't use it.

### Case 1: systematic review (ivermectin RCTs)

- **Final runs:** `runs/case1_systematic_review/baseline/sim/`, run indexes 1–5.
  - Runs 1 and 2 (`20261116T211756Z_1`, `20261116T212646Z_2`) were the v2 pilots, kept as final runs because their configuration was identical. They were then rescored with the final judge (DOC.md explains this).
  - Runs 3–5 (`20261116T214845Z_3`, `..._4`, `..._5`) were run in parallel.
  - Every run folder has `trajectory.json`, `reward.json`, `config.json` and `judgments.json`.
- **Pilots:** v1, 2 runs in `runs/_pilots/case1_systematic_review/v1/`. That folder is local only (gitignored), so teammates won't have it.
- **`summary.md`:** exists for the 5 runs and regenerates byte for byte.
  - Breakdowns: opaque screening 5/5, status ignored 2/5, missed key paper 0/5.
  - `recall_gold` 0.90, `rerun_overlap` 0.86.
- **Note:** `config.json` for runs 1–2 records `judge_model: claude-opus-5-5`, the judge at run time. They were rescored with Sonnet 5.5, which `judgments.json` records. Leave `config.json` as recorded; DOC.md section 6 should say this.

### Case 2: related work (algorithm aversion)

- **Final runs:** run indexes 1–5 (`20261116T223651Z_1` … `20261116T223659Z_5`), all with the four files.
- **Pilots:** v1, 1 run in `runs/pilots/case2_related_work/v1/`.
- **`summary.md`:** exists and regenerates byte for byte.
  - Breakdowns: missed key paper 5/5, opaque screening 4/5, misattribution 2/5, status ignored 0/5.
  - `recall_gold` 0.64, `rerun_overlap` 0.68.
- **Requested changes:** all three are done and visible in the final runs.
  - **All pair claims are judged.** 115 pair-citing statements across the 5 runs (21, 23, 30, 18 and 23), and every one has a label. Those outside the random sample were judged in a second call. Run 4 has re-judged labels, so the "must name a paper" rule was used.
  - **Turn-2 key-paper observation.** `observe_key_papers_at_turn: 2` is recorded in all 5 runs. In all 5, Dawes, Faust & Meehl 1989 was never seen by the end of turn 2 and is still missing from the final report, which is why missed key paper is 5/5. Dietvorst 2015 and Logg 2019 were included in every run.
  - **Dietvorst & Bharti 2020** (`W2974452734`) is in the corpus, labelled relevant and the third pair. 4 of 5 runs cite it, in 14 pair claims.
- **Open:** `pair_claims_review.md` (the 115 claims for hand-checking) has 0 of 115 checked. Some judge labels look wrong. In run 1, row 3 is labelled unsupported, but its rationale says the claim is supported. See step 4 below.

### Case 3: field map (social robots for older adults)

- **Final runs:** none. `runs/case3_field_map/baseline/sim/` is empty.
- **Pilots:** v1, 2 runs in `runs/pilots/case3_field_map/v1/`, rejected (see REJECTED.md). No v2 pilot yet.
- **`summary.md`:** none for final runs.
- **v2 changes:** all in `case.yaml`, validated and covered by tests. The new `case.yaml` hash is `fbac2459`; the v1 pilots used `48345f52`.
  - **Turn-2 message:** "Keep only studies with people living with dementia, and add any relevant ones you missed."
  - **Key papers:** 4 dementia studies (Liang 2017, Moyle 2013, Libin 2004, Valentí 2015).
  - **Observation:** `observe_key_papers_at_turn: 1`.
  - **Case metric:** `case_metrics: [post_change_recall]`, with `bd_steer_incomplete` firing below 0.6. It is written under `reward.json` `"case_metrics"`, so the core keys don't change.

### DOC.md sections

All three DOC.md files say "Sections 1–8 are written in Phase 4". So far they hold only design notes. **Partial** means some content exists that the section can reuse.

| Section | Case 1 | Case 2 | Case 3 | Where to get the content |
|---|---|---|---|---|
| 1. Setup and run instructions | missing | partial (corpus rebuild commands only) | missing | "Set up from a fresh clone" above, plus the CLAUDE.md commands |
| 2. Target breakdowns and why | partial ("Breakdowns not forced in sim mode", trap notes) | partial (hidden key paper, misattribution notes) | partial (post-change set, key papers, `post_change_recall`) | Planned cases table in CLAUDE.md |
| 3. Environment and reset | missing | missing | missing | Fresh container, `cases/` and `config/` mounted read-only, deterministic search |
| 4. External systems and mocking | missing | partial (frozen Semantic Scholar fallback) | partial (mocked search limits and ranking) | `corpus/SOURCES.md`; Anthropic API live; nothing writes to external systems |
| 5. Task and protocol, both modes | missing | missing | missing | `protocol.md`, `persona.md`, `shared/survey_interview.md` |
| 6. Baseline results | partial (notes on runs 1–2, observations) | missing | missing (needs final runs) | `summary.md`, plus observations and `trap_evidence` from `judgments.json` |
| 7. Proposed agent path | missing | missing | missing | Proposed agent section of CLAUDE.md |
| 8. Rejected cases | missing (REJECTED.md complete) | missing (REJECTED.md complete) | missing (REJECTED.md has v1; add v2 result) | Summarize `REJECTED.md` |

### Scoring consistency

- **Method.** `harness/metrics/replay.py`, new in this handoff, replays each run's stored judge answers through the **current** scoring code and compares the result with the stored files. It makes no API calls.
- **Result.** All 10 final `reward.json` files are identical under the current code, and all 5 case 2 `judgments.json` files are identical too. Case 2's runs were therefore scored with the v2 rules, even though their `config.json` records commit `4a8d80b`: they ran on uncommitted v2 code that was later committed as `f866dbd`.
- **Needs a free rescore: case 1 runs 1 and 5** (`20261116T211756Z_1`, `20261116T214849Z_5`). Each `judgments.json` is missing one `weak_check` note: a claim citing a record that has a title but no abstract, which the newer code marks. No metric changes. Step 1 below does it.
- **Case 3's v1 pilots** were scored before `case_metrics` existed. They're rejected pilots, so leave them as they are.
- **Core metric names are identical** across all 13 `reward.json` files in `runs/case*` and `runs/pilots/`: the 19 keys in `harness/metrics/names.py`. Only the 3 old local pilots in `runs/_pilots/` lack `near_miss_exclusion_rate`, which was added later.
- **Other checks.** `case.yaml`, the corpus and the baseline prompt hashes in every final `config.json` match the current files. The baseline prompt hasn't changed since the first commit.

### Team-level files

| File | Status |
|---|---|
| `README.md` | **missing**: needs links to each DOC.md, `shared/metrics.md` and `shared/survey_interview.md`, plus a "Created by / Tested by" table |
| `shared/metrics.md` | complete: all 19 core metrics, `rerun_overlap`, case 3's `post_change_recall` and `bd_steer_incomplete`, pair claims and the version rule |
| `shared/survey_interview.md` | complete: Raw NASA-TLX (5 scales), 8 Likert items, 5 interview questions; `harness/survey/survey.py` asks the same questions |

### Cost

Rates: Opus 5.5 is $4 input, $20 output, $0.20 cache read and $5 cache write (5-minute TTL) per million tokens. Sonnet 5.5 is $2, $10, $0.10 and $2.50. The agent uses Opus; the sim user and judge use Sonnet. My calculation reproduces the case 2 v1 pilot at exactly the $1.54 its REJECTED.md gives.

**Spent so far (from the run records):**

| What | Runs | Cost | Per run |
|---|---|---|---|
| Toy pilot | 1 | $0.41 | |
| Case 1 v1 pilots (local) | 2 | $3.30 | $1.65 |
| Case 1 final | 5 | $15.07 | $3.01 |
| Case 2 v1 pilot | 1 | $1.54 | |
| Case 2 final | 5 | $8.11 | $1.62 |
| Case 3 v1 pilots | 2 | $2.50 | $1.25 |
| **Recorded total** | 16 | **$30.93** | |
| Not recorded: judge calls overwritten by rescores (case 1 runs 1–2 first used an Opus judge; case 3 pilots were rescored) | | about $3 | |
| **Estimated total** | | **about $34** | |

For the exact figure, see the Anthropic Console's usage page.

**Remaining paid steps (estimates):**

| Step | Runs | Estimate |
|---|---|---|
| Case 3 v2 pilot (step 2) | 2 | $5.50 |
| Case 3 final runs 3–5, keeping the pilots as runs 1–2 (step 3) | 3 | $8.25 |
| *If the pilots can't be kept: 5 new final runs instead* | *5* | *$13.75* |
| Fresh-clone check, 1 sim run per case (step 8) | 3 | $7.50 |
| *Optional: 1 human-mode test run per case (step 6)* | *3* | *$7* |
| Case 1 rescore (step 1) | – | $0 |

Case 3 is estimated at $2–3.50 per run, about $2.75. v1 cost $1.25 per run, but it stopped after 40 tool calls in turn 1. v2's turn 2 asks the agent to search again, so expect case 1-like costs.

**Projected total:** about $55 for the base plan (pilots kept, no human runs). Each of the following pushes it past the **$60 cap**, so check with the team first: 5 new case 3 finals (about $61), a second case 3 pilot round (+$5.50), or the optional human runs (+$7).

| Running total (update as you go) | Who | Step | Cost | Total |
|---|---|---|---|---|
| | | handoff-1 | | about $34 |

## Remaining work, in order

People can work on items 4, 5 and 7 while items 2–3 run.

- [ ] **1. Free rescore of case 1 runs 1 and 5** (free, 2 min)
  ```bash
  docker compose run --rm -e ANTHROPIC_API_KEY= harness python -m harness.metrics.replay --write \
    runs/case1_systematic_review/baseline/sim/20261116T211756Z_1 \
    runs/case1_systematic_review/baseline/sim/20261116T214849Z_5
  docker compose run --rm -e ANTHROPIC_API_KEY= harness sh -c \
    'python -m harness.metrics.replay runs/case1_systematic_review/baseline/sim/2026*'   # all "up to date"
  python3 -m harness.metrics.summarize --case case1_systematic_review                    # summary.md unchanged
  git add runs/case1_systematic_review
  git commit -m "data(case1): add weak_check marks to runs 1 and 5 via free replay"
  ```
- [ ] **2. Case 3 v2 pilot, 2 runs** (paid, about $5.50, 10–20 min; **ask first**)
  ```bash
  docker compose run --rm harness python -m harness.run --case case3_field_map --mode sim --agent baseline --runs 2
  python3 -m harness.metrics.summarize --case case3_field_map
  cat runs/case3_field_map/baseline/sim/summary.md
  ```
  To run both pilots at once, use two terminals with `--runs 1 --start-index 1` and `--runs 1 --start-index 2`.
  - **Pass** means at least one target breakdown fires in at least one run: `bd_scope_drift`, `bd_cant_steer` or `bd_steer_incomplete` (under `case_metrics`). Also check `rerun_overlap`.
  - **If it passes**, keep the two runs as final runs 1–2, as case 1 did with identical configuration, and note this in DOC.md.
  - **If it fails**, move both runs to `runs/pilots/case3_field_map/v2/` and log v2 in REJECTED.md. Then decide as a team whether a v3 fits the time and budget left (about $5.50 per pilot round).
- [ ] **3. Case 3 final runs 3–5** (paid, about $8.25; **ask first**). Use three terminals:
  ```bash
  docker compose run --rm harness python -m harness.run --case case3_field_map --mode sim --agent baseline --runs 1 --start-index 3
  docker compose run --rm harness python -m harness.run --case case3_field_map --mode sim --agent baseline --runs 1 --start-index 4
  docker compose run --rm harness python -m harness.run --case case3_field_map --mode sim --agent baseline --runs 1 --start-index 5
  # then, free:
  docker compose run --rm -e ANTHROPIC_API_KEY= harness sh -c 'python -m harness.metrics.replay runs/case3_field_map/baseline/sim/2026*'
  python3 -m harness.metrics.summarize --case case3_field_map
  git add runs/case3_field_map cases/case3_field_map/REJECTED.md
  git commit -m "data(case3): add 5 final baseline runs and summary"
  ```
  The commit body should list the command, the models and the `bd_*` counts (see CONTRIBUTING.md).
- [ ] **4. Hand-check case 2's pair claims** (free, about 45 min, one person)
  - Open `runs/case2_related_work/baseline/sim/pair_claims_review.md`. Tick `ok` when you agree with a label; otherwise write a note.
  - Start with the 3 `misattributed` labels behind `bd_misattribution` 2/5: run 3, rows 19 and 27, and run 5, row 13. Then check run 1, row 3.
  - Don't edit `judgments.json` or `reward.json`. Report the agreement rate, and any flag the check would overturn, next to the judge's numbers in DOC.md section 6. **Team decision:** whether a disagreement changes the reported breakdown count.
- [ ] **5. Complete DOC.md for all three cases** (free). Use the Phase 4 prompt in CLAUDE.md and the DOC.md table above. Case 3's section 6 has to wait for step 3.
- [ ] **6. Optional: one human-mode test run per case** (paid, about $7; **ask first**). These fill the "Tested by" column and test the survey.
  ```bash
  docker compose run --rm harness python -m harness.run --case case1_systematic_review --mode human --agent baseline
  ```
  Repeat for cases 2 and 3. Type `/done` to finish; the survey follows in the terminal. The interviewer then fills in `interview_notes.md` in the run folder.
- [ ] **7. Write `README.md`** (free). Cover how to build and run (from "Set up from a fresh clone"), and link each DOC.md, `shared/metrics.md`, `shared/survey_interview.md`, CONTRIBUTING.md and this file. Add the "Created by / Tested by" table, one row per case.
- [ ] **8. Fresh-clone check (Phase 5)** (paid, about $7.50; **ask first**)
  ```bash
  cd "$(mktemp -d)" && git clone https://github.com/BhanuHarshaY/researcher.git && cd researcher
  cp ~/path/to/your/.env .env
  docker compose build
  docker compose run --rm -e ANTHROPIC_API_KEY= harness python -m unittest discover -s tests -t .
  for c in case1_systematic_review case2_related_work case3_field_map; do
    docker compose run --rm -e ANTHROPIC_API_KEY= harness python -m corpus_tools.validate $c
  done
  for c in case1_systematic_review case2_related_work case3_field_map; do   # paid
    docker compose run --rm harness python -m harness.run --case $c --mode sim --agent baseline --runs 1
  done
  git ls-files | grep -E '(^|/)\.env$|\.tar(\.gz)?$' || echo "no keys or images tracked"
  ```
  - Follow README.md and each DOC.md literally, and fix any step that fails or is unclear in the main repo.
  - These runs stay in the temp clone. **Don't commit them**, or they'll mix into the final summaries.
  - Cheaper option: add `--no-score` (saves about $1.50), or run `_toy` only (about $0.40).
- [ ] **9. Tags** (free)
  ```bash
  git tag -a baseline-runs-complete -m "Baseline: 5 final sim runs for each of the 3 cases"   # after step 3
  git tag -a submission -m "CS 6983 Team 6 submission"                                      # last commit before 23:59
  git push origin main --tags
  ```
- [ ] **10. Video** (requirements aren't in the repo: **check the assignment for length and content**)
  - Suggested outline: a fresh clone and `docker compose build` → one sim run, showing the output folder (`trajectory.json`, `reward.json`, `config.json`) → a human-mode run with the survey → each case's `summary.md` and its breakdowns → the DOC.md layout.
  - Record against existing runs where you can, so recording doesn't spend.
  - Put the link in README.md.
