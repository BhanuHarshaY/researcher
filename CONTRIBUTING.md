# Contributing

How we name branches and write commits in this repo. Keep `main` working: every commit on `main` should build in Docker and pass the unit tests.

## Branches

Do your work on a branch and merge it into `main` with a pull request.

Format: `<type>/<scope>-<short-description>`

- `type` is one of the commit types below.
- `scope` is one of the commit scopes below.
- `short-description` is 2–4 words, lowercase, joined by hyphens.
- Keep the whole name under about 40 characters. Use no spaces, capital letters or underscores (except in the case folder names, which we shorten anyway, e.g. `case2`).

Examples:

```
feat/case2-hidden-key-paper
fix/tools-search-year-filter
data/case1-final-runs
docs/case3-doc
test/metrics-steer-preservation
chore/docker-pin-deps
```

Delete the branch after it is merged.

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>
```

### Types

| Type | Use for |
|---|---|
| `feat` | New behaviour: a harness feature, a new metric, a new case |
| `fix` | A bug fix |
| `data` | Corpus snapshots, labels, `case.yaml` gold or trap changes, committed run outputs |
| `docs` | `README.md`, `DOC.md`, `shared/*.md`, `CONTRIBUTING.md` |
| `test` | Adding or changing unit tests only |
| `refactor` | Code changes that don't change behaviour or outputs |
| `chore` | Docker, dependencies, `.gitignore`, other housekeeping |

### Scopes

Use the part of the repo you changed:

| Scope | Covers |
|---|---|
| `harness` | `run.py`, `channel.py`, `recorder.py`, `config.py` |
| `agents` | `harness/agents/` (baseline and proposed) |
| `users` | `harness/users/` (sim user and human user) |
| `tools` | `harness/tools/mock_search.py` |
| `metrics` | `harness/metrics/` |
| `survey` | `harness/survey/` |
| `corpus` | `corpus_tools/` |
| `case1`, `case2`, `case3`, `toy` | Everything inside one case folder, plus its runs |
| `shared` | `shared/` |
| `docker` | `Dockerfile`, `docker-compose.yml` |
| `config` | `config/models.yaml`, `.env.example` |

If a commit touches several areas, use the main one. If no single scope fits, leave it out: `docs: add top-level README`.

### Subject line

- Imperative mood: "add", "fix", "rescore", not "added" or "fixes".
- Lowercase, no full stop at the end.
- 72 characters or fewer, including the `type(scope):` prefix.
- Say what changed, not how you felt about it: `fix(tools): exclude hidden papers from search_papers`, not `fix: bug fix`.

### Body

Add a body for anything beyond a one-line change. Leave a blank line after the subject and wrap lines at 72 characters.

- Use `-` bullets, one change per bullet.
- Say what changed and why. The diff already shows how.
- Note anything that changes results, e.g. "reward.json gains a field; rescore older runs with `harness.metrics.score`".

For commits that add run outputs (`data(caseN): ...`), also include:

- the command you ran and the number of runs
- the agent model (from `config/models.yaml`)
- which `bd_*` flags fired and in how many runs, e.g. `opaque screening 5/5, status ignored 2/5`

### Footer

- Breaking changes: add `!` after the scope and a `BREAKING CHANGE:` line saying what breaks, e.g. a `trajectory.json` or `config.json` format change that old runs don't match. Core metric names in `reward.json` are fixed, so never rename them.
- Do **not** add `Co-Authored-By` trailers for AI tools.

### Examples

```
feat(metrics): add near_miss_exclusion_rate core metric

- Near-miss papers left out of the final report ÷ near-misses in the corpus
- Reads near_miss_ids from case.yaml; null when a case has none
- Older runs need rescoring with harness.metrics.score to include it
```

```
fix(tools): hide status from get_paper results
```

```
data(case1): add 5 final baseline runs and summary

- docker compose run --rm harness python -m harness.run \
    --case case1_systematic_review --mode sim --agent baseline --runs 5
- Agent model from config/models.yaml, temperature 1.0
- Breakdowns: opaque screening 5/5, status ignored 2/5,
  missed key paper 0/5
```

## Before you commit

- [ ] Unit tests pass: `python -m unittest discover -s tests -t .`
- [ ] No API keys or contact emails in the diff. `.env` stays uncommitted; only `.env.example` is tracked.
- [ ] No Docker images or archives (`*.tar`, `*.tar.gz`).
- [ ] Model names appear only in `config/models.yaml`.
- [ ] `harness/agents/baseline_prompt.md` is unchanged. It is frozen after the first committed run.
- [ ] Final runs go in `runs/<case>/`. A pilot that a `REJECTED.md` cites goes in `runs/pilots/<case>/<variant>/` and is committed. Scratch runs go in `runs/_pilots/` (gitignored).
- [ ] Paid commands (`harness.run`, `harness.metrics.score`) were agreed with the team first (see HANDOFF.md).
- [ ] Corpus files under `cases/*/corpus/` change only through `corpus_tools/`, never by hand.
