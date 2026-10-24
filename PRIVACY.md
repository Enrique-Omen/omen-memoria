# Privacy · OMEN Memoria

- The plugin only reads and writes its own files under `.omen-memoria/` in your project (`MEMORY.md`, `seen/`, `.lock`, `.gitignore`).
- It never reads Claude's own memory, your chat history or transcripts. To find the project root it only checks whether `.git` or `.omen-memoria` exists; it reads no other file.
- No network access at all: no telemetry, analytics, accounts or updates. OMEN receives nothing.
- It refuses text that matches common secret patterns (OpenAI, Stripe, Google, GitHub, AWS and Slack keys, PEM blocks, `password=`), and the skill tells Claude never to store secrets. It is a safety net, not a guarantee.
- `MEMORY.md` is shown to Claude at session start: review changes to it like any other committed file.
- Claude sees what the tools return (and the SessionStart summary); that is governed by your Claude account terms.
- `.omen-memoria/MEMORY.md` is plain text: you decide whether to commit it. The per-machine marks (`seen/`, `.lock`) are git-ignored.

Contact: contacto@omen-it.tech

## Privacidad (español)
Solo lee y escribe sus propios archivos en `.omen-memoria/` de tu repo. Nunca lee la memoria de Claude, tu historial ni transcripciones. Sin red, sin telemetría. Rechaza secretos. Contacto: contacto@omen-it.tech
