# Lit-review agent test cases (CS 6983, Team 6)

A resettable test environment for literature-review agents. Each of the three
test cases gives an agent a research request, a frozen corpus of real papers
behind a mocked search tool, and a user to talk to: either a simulated user
(`sim` mode) or a person typing in the terminal (`human` mode). Both modes use
the same chat channel. Every run is scored with the same core metrics and
written to its own output folder.

The baseline agent is modelled on Claude Research. The proposed agent is a stub
for now; each case's DOC.md, section 7, describes how it will run.

## Test cases

| Case | Task | Target breakdowns | Source review | Doc |
|---|---|---|---|---|
| `case1_systematic_review` | Systematic review of RCTs of ivermectin for COVID-19, with criteria revealed over the first turns | Opaque screening, missed key paper, status ignored (retracted papers, superseded preprints) | Marcolino et al. 2022, *BMC Infect Dis* | [DOC.md](cases/case1_systematic_review/DOC.md) |
| `case2_related_work` | Related-work section on relying on algorithms vs. human judgment | Misattribution between similar papers, missed key paper (one is reachable only through citations) | Castelo et al. 2019, *J Marketing Research* | [DOC.md](cases/case2_related_work/DOC.md) |
| `case3_field_map` | Map the field of social robots for older adults, then narrow it to dementia | Scope drift, can't steer, not reproducible | Mahmoudi Asl et al. 2022, *J Med Internet Res* | [DOC.md](cases/case3_field_map/DOC.md) |

`cases/_toy/` is a 10-paper case for checking the harness end to end.

Shared across all cases:
- [shared/metrics.md](shared/metrics.md): definitions of every core metric in `reward.json`.
- [shared/survey_interview.md](shared/survey_interview.md): the post-run survey and interview for human mode.

## Created by / Tested by

| Case | Created by | Tested by |
|---|---|---|
| Case 1: systematic review | Vishwani Singh | Wendi Shi |
| Case 2: related work | Bhanu Harsha Yanamadala | Vishwani Singh |
| Case 3: field map | Wendi Shi | Bhanu Harsha Yanamadala |

The tester of each case is a teammate who did not create it. They set up and
ran the case from a fresh clone using only its DOC.md, and recorded the video.

## Setup

You need Docker with Compose and an Anthropic API key.

```bash
git clone https://github.com/BhanuHarshaY/researcher.git
cd researcher
cp .env.example .env      # put your key in .env: ANTHROPIC_API_KEY=...  (never commit .env)
docker compose build
```

Free checks. Blanking the key with `-e ANTHROPIC_API_KEY=` makes it impossible
for these commands to spend money:

```bash
docker compose run --rm -e ANTHROPIC_API_KEY= harness python -m unittest discover -s tests -t .
for c in _toy case1_systematic_review case2_related_work case3_field_map; do
  docker compose run --rm -e ANTHROPIC_API_KEY= harness python -m corpus_tools.validate $c
done
```

Expected: `Ran 78 tests ... OK`, then `OK` for each case.

## Running a case

These commands call the Anthropic API and **cost money**. A sim run costs about
$1–3, depending on the case and the model.

```bash
# Simulated user, 5 runs
docker compose run --rm harness python -m harness.run --case case1_systematic_review --mode sim --agent baseline --runs 5

# You play the user. Type /done to finish; the survey follows in the terminal.
docker compose run --rm harness python -m harness.run --case case1_systematic_review --mode human --agent baseline
```

Useful options for `harness.run`:
- `--start-index N`: number the runs from N, so several terminals can run in parallel without clashing.
- `--no-score`: skip the LLM judge, which saves about $0.50 per run.

Summarize the runs of a case (free; uses only the Python standard library, so it
also runs on the host):

```bash
python3 -m harness.metrics.summarize --case case1_systematic_review
```

Re-score stored runs with the current scoring code, replaying the stored judge
answers (free, no API calls):

```bash
docker compose run --rm -e ANTHROPIC_API_KEY= harness sh -c 'python -m harness.metrics.replay runs/case1_systematic_review/baseline/sim/2026*'
```

## What a run produces

Each run writes `runs/<case>/<agent>/<mode>/<UTC timestamp>_<n>/`:

| File | Contents |
|---|---|
| `trajectory.json` | Every user message, agent message, tool call and tool result, in order, with timestamps and token usage |
| `reward.json` | The core metrics and `bd_*` breakdown flags, with the same keys for every case |
| `config.json` | Case, mode, agent, models, prompt / corpus / `case.yaml` hashes, git commit, limits, start time |
| `judgments.json` | The judge's labels behind the metrics |
| `survey.json`, `interview_notes.md` | Human mode only |

`summarize` adds `summary.json` and `summary.md` to `runs/<case>/<agent>/<mode>/`,
with mean metrics, `rerun_overlap` across runs and how many runs showed each
breakdown.

## Environment and reset

- Every run starts in a fresh container. `cases/` and `config/` are mounted
  read-only, so a run cannot change a corpus, a case or the models.
- Search is mocked from each case's frozen corpus (`cases/<case>/corpus/papers.jsonl`)
  and is deterministic. Variation between runs comes only from the models.
- The Anthropic API is the only live external system. Nothing writes to any
  external system.

## Models

Model names live only in [config/models.yaml](config/models.yaml), and each
run's `config.json` records the models it used.

- Cases 1 and 2: the final baseline runs used **Opus 5.5** as the agent model.
- Case 3, and every run from commit `716d20e` onward: **Sonnet 5.5**, for budget
  reasons. Re-running case 1 or 2 from the current repo therefore uses Sonnet
  and won't reproduce those baselines exactly.
- The simulated user and the judge use Sonnet 5.5 in every case.

## Repo layout

```
harness/        run.py (entry point), chat channel, recorder, agents, users, mock search, metrics, survey
corpus_tools/   dev-time corpus builder (OpenAlex / PubMed / Crossref) and validator
cases/          one folder per case: case.yaml, frozen corpus, persona, protocol, DOC.md, REJECTED.md
shared/         metrics and survey documents shared by all cases
config/         pinned model names
runs/           committed baseline runs (runs/pilots/ holds the pilots cited by REJECTED.md)
tests/          unit tests
```

## More

- [CLAUDE.md](CLAUDE.md): the full spec.
- [CONTRIBUTING.md](CONTRIBUTING.md): branch and commit conventions.
- Videos (each recorded by the case's tester from a fresh clone, following only its DOC.md):
  - Case 1 (tested by Wendi Shi): _link to add_
  - Case 2 (tested by Vishwani Singh): [video](https://drive.google.com/file/d/1camCryHDdaBF9USi7gsTFIBEzRRYe6lX/view?usp=drive_link)
  - Case 3 (tested by Bhanu Harsha Yanamadala): _link to add_
