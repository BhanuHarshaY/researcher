# Protocol: `_toy` (harness test fixture)

This is a 10-paper **synthetic** corpus used only to test the harness end to end.
It is not one of the three submitted cases.

The paper set covers every tool path: 4 gold (T001 and T004 are key), 1 other
relevant paper, 2 off-scope papers, a superseded preprint (T006 → T001), a
retracted paper (T007) and a hidden gold paper (T004). T004 can only be reached
through `get_references` / `get_citations`.

**Sim mode.** Turn 1 sends `initial_prompt`. After the agent's first reply, the
sim user asks why T004 was not included. After that, the persona decides whether
to continue or send `/done` (at most 6 user turns).

**Human mode.** Turn 1 sends `initial_prompt` automatically. The person then
types follow-ups. End a message with an empty line, and type `/done` to finish.

```
docker compose run --rm harness python -m harness.run --case _toy --mode sim --agent baseline
docker compose run --rm harness python -m harness.run --case _toy --mode human --agent baseline
```
