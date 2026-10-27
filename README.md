# OMEN Memoria

Claude forgets what your team decided between sessions. OMEN Memoria keeps a short decision diary in your repo, so every agent starts knowing the current decisions and only what changed since it last looked.

Install in Claude Code (macOS and Linux; on Windows, use WSL):

```
/plugin marketplace add Enrique-Omen/omen-memoria
/plugin install omen-memoria@omen-memoria
```

Then try: "Laura decided we use PostgreSQL. Record it." Next session, any agent: "What has the team decided?"

Everything stays in one readable file, `.omen-memoria/MEMORY.md`, inside your repo. No network.

## What makes it different

1. **A decision diary as its own entry type.** `decision` (made by a human, needs `--by`), `agreed` (your reversible choice, needs `--undo`). A newer entry on the same `topic` replaces the old one; an `agreed` can never replace a human `decision`.
2. **Only what is new.** At session start each agent sees the current decisions plus just what OTHER agents wrote since its own last session (never more than ~4 KB).
3. **Several agents, one memory.** Writes are serialized with a file lock (`fcntl.flock`); two agents writing at once never corrupt the file.

## File format

One line per entry, newest last. `source` and `topic` are optional:

```
2026-10-24 01:50 · ana · decision · Use Postgres for billing (by Laura) · docs/db.md · topic: db
```

Types: `decision`, `agreed`, `proposed`, `done`, `lesson`. Max 280 characters; for more, put the detail in a file and cite it with `--source`. Text that matches common secret patterns (OpenAI, Stripe, Google, GitHub, AWS and Slack keys, PEM blocks, `password=`) is refused, and the skill tells Claude never to store secrets. It is a safety net, not a guarantee.

## Tools

A Claude Code plugin: an MCP server, an Agent Skill and a SessionStart hook, in Python's standard library.

| Tool | Use |
|---|---|
| `memory_write` | Record a decision, a reversible choice, a session closure or a lesson. |
| `memory_search` | Search before re-deciding or re-trying (accent- and case-insensitive; all words must match). |
| `memory_current` | The current decisions (newest per topic). |
| `memory_new` | What the hook shows at start, on demand. Moves your "seen" mark. |

The project root is `$OMEN_MEMORIA_DIR` if set, otherwise the current directory, climbing up to the first `.git` or `.omen-memoria`. The agent name is `--agent` or `$OMEN_MEMORIA_AGENT` (default `claude`).

Give each agent or person its own name (`export OMEN_MEMORIA_AGENT=ana` before launching `claude`): entries under your own name are never shown to you as new.

## From a local copy

`claude --plugin-dir ./omen-memoria`. On Windows, `fcntl` is not available: use WSL or macOS/Linux.

## Command line

```bash
python3 skills/team-memory/scripts/memoria.py write decision "Use Postgres" --by Laura --topic db
python3 skills/team-memory/scripts/memoria.py write agreed "Renamed the module" --undo "git revert abc123"
python3 skills/team-memory/scripts/memoria.py start --agent ana
python3 skills/team-memory/scripts/memoria.py search postgres
python3 skills/team-memory/scripts/memoria.py current
python3 skills/team-memory/scripts/memoria.py mcp     # MCP server over stdio
```

Tests: `python3 -m unittest discover -s tests -v`.

## Examples

Three real sessions, two agents, one repo (Claude Sonnet, Oct 2026):

1. `ana`: *"Laura, our tech lead, decided: PostgreSQL, not MySQL. Record it."* → `decision` by Laura, topic `database`.
2. `beto`: *"What has the team decided and what is new since my last session? Laura changed her mind: SQLite for now."* → the hook already showed ana's entries; the new `decision` replaces the old one on the same topic.
3. `ana`: *"Which database do we use right now?"* → answered "SQLite for now" in one turn, from the start summary alone.

## Troubleshooting

- **Nothing shows at session start:** there is no `.omen-memoria/MEMORY.md` yet. `start` stays silent on purpose until the first entry.
- **The hook did not run:** ask Claude to call `memory_new`; it returns the same summary.
- **`python3` not found:** it must be on your `PATH` (on macOS, install the Xcode Command Line Tools).

## Privacy

Only reads and writes its own files in `.omen-memoria/` of your repo. Never reads Claude's memory, history or transcripts. No network. See [PRIVACY.md](PRIVACY.md).

## Limits

- Unix only (`fcntl`).
- Not a search engine or a vector store: it is a short, human-readable diary.
- The marks in `.omen-memoria/seen/` are per machine (git-ignored); a fresh clone sees everything by others as new once.

## En español

Memoria de equipo para uno o varios agentes en un repo, en un archivo de texto legible (`.omen-memoria/MEMORY.md`). Lo que la distingue: el diario de decisiones (la nueva del mismo tema reemplaza a la vieja; una decisión de un humano la anota el agente con `--by`), al arrancar cada agente ve solo lo nuevo desde su última sesión más las decisiones vigentes, y varios agentes comparten la misma memoria con candado. Solo toca `.omen-memoria/` de tu repo, sin red ni lectura de tu historial. Solo macOS/Linux.

---

Made by OMEN · [omen-it.tech](https://omen-it.tech) · contacto@omen-it.tech
