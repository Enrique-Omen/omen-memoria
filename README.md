# OMEN Memoria

Team memory for one or several agents in a repo, in one readable text file: `.omen-memoria/MEMORY.md`. A Claude Code plugin (MCP server + Agent Skill + SessionStart hook). Python 3 standard library only.

## What makes it different

1. **A decision diary as its own entry type.** `decision` (made by a human, needs `--by`), `agreed` (your reversible choice, needs `--undo`). A newer entry on the same `topic` replaces the old one; an `agreed` can never replace a human `decision`.
2. **Only what is new.** At session start each agent sees the current decisions plus just what OTHER agents wrote since its own last session (never more than ~4 KB).
3. **Several agents, one memory.** Writes are serialized with a file lock (`fcntl.flock`); two agents writing at once never corrupt the file.

## File format

One line per entry, newest last. `source` and `topic` are optional:

```
2026-10-24 01:50 · ana · decision · Use Postgres for billing (by Enrique) · docs/db.md · topic: db
```

Types: `decision`, `agreed`, `proposed`, `done`, `lesson`. Max 280 characters; for more, put the detail in a file and cite it with `--source`. Text that looks like a secret is refused.

## Tools

| Tool | Use |
|---|---|
| `memory_write` | Record a decision, a reversible choice, a session closure or a lesson. |
| `memory_search` | Search before re-deciding or re-trying (no accents, no case, all words). |
| `memory_current` | The current decisions (newest per topic). |
| `memory_new` | What the hook shows at start, on demand. Moves your «seen» mark. |

The project root is `$OMEN_MEMORIA_DIR` if set, otherwise the current directory, climbing up to the first `.git` or `.omen-memoria`. The agent name is `--agent` or `$OMEN_MEMORIA_AGENT` (default `claude`).

## Install in Claude Code

```
/plugin marketplace add Enrique-Omen/omen-memoria
/plugin install omen-memoria@omen
```

From a local copy: `claude --plugin-dir ./omen-memoria`. On Windows, `fcntl` is not available: use WSL or macOS/Linux.

## Command line

```bash
python3 skills/team-memory/scripts/memoria.py write decision "Use Postgres" --by Enrique --topic db
python3 skills/team-memory/scripts/memoria.py write agreed "Renamed the module" --undo "git revert abc123"
python3 skills/team-memory/scripts/memoria.py start --agent ana
python3 skills/team-memory/scripts/memoria.py search postgres
python3 skills/team-memory/scripts/memoria.py current
python3 skills/team-memory/scripts/memoria.py mcp     # MCP server over stdio
```

Tests: `python3 -m unittest discover -s tests -v`.

## Privacy

Only reads and writes its own files in `.omen-memoria/` of your repo. Never reads Claude's memory, history or transcripts. No network. See [PRIVACY.md](PRIVACY.md).

## Limits

- Unix only (`fcntl`).
- Not a search engine or a vector store: it is a short, human-readable diary.
- The marks in `.omen-memoria/seen/` are per machine (git-ignored); a fresh clone sees everything by others as new once.

## En español

Memoria de equipo para uno o varios agentes en un repo, en un archivo de texto legible (`.omen-memoria/MEMORY.md`). Lo que la distingue: el diario de decisiones (la nueva del mismo tema reemplaza a la vieja; una decisión de un humano la anota el agente con `--by`), al arrancar cada agente ve solo lo nuevo desde su última sesión más las decisiones vigentes, y varios agentes comparten la misma memoria con candado. Solo toca `.omen-memoria/` de tu repo, sin red ni lectura de tu historial. Solo macOS/Linux.
