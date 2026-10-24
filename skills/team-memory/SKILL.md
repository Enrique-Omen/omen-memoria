---
name: team-memory
description: Shared team memory for one or several agents working in the same repo, kept in a plain-text file (.omen-memoria/MEMORY.md). Use it at the start of work to see what is new and which decisions are current, before re-deciding or re-trying something (search first), and to record a human decision, a reversible choice of yours, a session closure or a lasting lesson. Usa esta skill para la memoria compartida del equipo: decisiones vigentes, lo nuevo desde tu última sesión y cierres de sesión.
---

# Team memory (OMEN Memoria)

One file, one line per entry, newest last: `.omen-memoria/MEMORY.md` at the project root. With the plugin installed the tools are `memory_write`, `memory_search`, `memory_current`, `memory_new`; the SessionStart hook already shows you the current decisions and only what OTHER agents wrote since your last session. Without MCP, the same from the shell:

```bash
python3 scripts/memoria.py write <type> "<text>" [--source FILE] [--topic T] [--by NAME] [--undo HOW] [--agent A]
python3 scripts/memoria.py start | current | search <words>
```

## When to write

| Situation | Type | Needs |
|---|---|---|
| A human decided something (said it in chat, approved a plan) | `decision` | `--by <human name>`. You only record it; never invent one. |
| You chose something reversible | `agreed` | `--undo "<how to undo it>"` |
| You suggest something not yet decided | `proposed` | |
| End of session: what you did and where to see it | `done` | `--source <file or link>` |
| A lesson that will still be true next month | `lesson` | |

- Use `--topic <one-word>` on decisions: a newer `decision`/`agreed` on the same topic replaces the older one. An `agreed` can never replace a human `decision`: ask the human.
- Max 280 characters per entry. If you need more, put the detail in a file of the project and cite it with `--source`.
- Agent name: `--agent` or `$OMEN_MEMORIA_AGENT` (default `claude`). Use the same name every session so «new» works.

## When NOT to write

- What is already in the code or in git history.
- What only matters to this conversation.
- Secrets of any kind (tokens, passwords, keys): the tool refuses them.

## Before fighting with something

`memory_search` first (accent- and case-insensitive, all words must match). Someone may have decided or learned it already.

## En español

Memoria compartida del equipo en `.omen-memoria/MEMORY.md`. Escribe `decision` (con `--by`, la toma un humano), `agreed` (con `--undo`), `done` al cerrar y `lesson` si dura. Busca antes de pelear con algo. Máx. 280 caracteres: el detalle va en un archivo y la línea lo cita. Nunca secretos.
