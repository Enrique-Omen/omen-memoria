# Privacy · OMEN Memoria

- The plugin only reads and writes its own files under `.omen-memoria/` in your project (`MEMORY.md`, `seen/`, `.lock`).
- It never reads Claude's own memory, your chat history or transcripts, or any other file.
- No network access at all: no telemetry, analytics, accounts or updates. OMEN receives nothing.
- It refuses to store text that looks like a secret (API keys, tokens, passwords, private keys).
- Claude sees what the tools return (and the SessionStart summary); that is governed by your Claude account terms.
- `.omen-memoria/MEMORY.md` is plain text: you decide whether to commit it. The per-machine marks (`seen/`, `.lock`) are git-ignored.

Contact: contacto@omen-it.tech

## Privacidad (español)
Solo lee y escribe sus propios archivos en `.omen-memoria/` de tu repo. Nunca lee la memoria de Claude, tu historial ni transcripciones. Sin red, sin telemetría. Rechaza secretos. Contacto: contacto@omen-it.tech
