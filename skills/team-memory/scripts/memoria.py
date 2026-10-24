#!/usr/bin/env python3
"""OMEN Memoria: shared team memory in one readable text file (.omen-memoria/MEMORY.md).

One line per entry, newest last. Standard library only. No network. Reads and writes only
its own files under .omen-memoria/ of the project.
  memoria.py write|start|search|current|mcp
"""
import argparse
import fcntl
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

NOMBRE, VERSION = "omen-memoria", "0.1.0"
TIPOS = ("decision", "agreed", "proposed", "done", "lesson")
MAX_TEXTO, MAX_EXTRA, MAX_SALIDA = 280, 100, 4000
NO_HUMANOS = {"claude", "assistant", "ai", "agent", "bot", "gpt", "codex"}
SECRETO = re.compile(
    r"sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}"
    r"|xox[bp]-[A-Za-z0-9-]{8,}|-----BEGIN"
    r"|\b(password|passwd|token|api[_-]?key|secret)\s*=\s*\S+", re.I)


class ErrorUso(Exception):
    pass


# ---------------------------------------------------------------- store
def raiz():
    inicio = Path(os.environ.get("OMEN_MEMORIA_DIR") or os.getcwd()).resolve()
    for d in (inicio, *inicio.parents):
        if (d / ".omen-memoria").is_dir() or (d / ".git").exists():
            return d
    return inicio


def _agente(agent):
    a = agent or os.environ.get("OMEN_MEMORIA_AGENT") or "claude"
    if not re.fullmatch(r"[a-z0-9_-]+", a):
        raise ErrorUso(f"Invalid agent name {a!r}: use only [a-z0-9_-].")
    return a


def _leer(archivo):
    entradas = []
    if not archivo.exists():
        return entradas
    for n, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
        p = linea.split(" · ")
        if len(p) < 4:
            continue
        e = {"n": n, "ts": p[0], "agent": p[1], "type": p[2], "text": p[3], "source": None, "topic": None, "raw": linea}
        for extra in p[4:]:
            if extra.startswith("topic: "):
                e["topic"] = extra[7:]
            else:
                e["source"] = extra
        entradas.append(e)
    return entradas


def _vigentes(entradas):
    """decision/agreed: per topic the newest wins; without topic all count."""
    ultima = {e["topic"]: e["n"] for e in entradas if e["type"] in ("decision", "agreed") and e["topic"]}
    return [e for e in entradas if e["type"] in ("decision", "agreed") and (not e["topic"] or ultima[e["topic"]] == e["n"])]


class _Candado:
    def __enter__(self):
        os.makedirs(raiz() / ".omen-memoria", exist_ok=True)
        self.f = open(raiz() / ".omen-memoria" / ".lock", "a")
        fcntl.flock(self.f, fcntl.LOCK_EX)

    def __exit__(self, *a):
        self.f.close()


def _limpio(s):
    return " ".join(str(s).replace("·", "-").split())


def _fmt(e):
    return f"{e['ts']} {e['agent']} {e['type']}: {e['text']}" + (f" [{e['source']}]" if e["source"] else "") + \
           (f" (topic: {e['topic']})" if e["topic"] else "")


# ---------------------------------------------------------------- tools
def escribir(type, text, source=None, topic=None, by=None, undo=None, agent=None):
    agente = _agente(agent)
    if type not in TIPOS:
        raise ErrorUso(f"Unknown type {type!r}: use one of {', '.join(TIPOS)}.")
    text, source, topic, by, undo = (_limpio(x) if x else None for x in (text, source, topic, by, undo))
    if not text:
        raise ErrorUso("Empty text.")
    if len(text) > MAX_TEXTO:
        raise ErrorUso(f"Text is {len(text)} characters (max {MAX_TEXTO}): put the detail in a file and cite it "
                       "in the line with --source.")
    if SECRETO.search(" ".join(x for x in (text, source, topic, by, undo) if x)):
        raise ErrorUso("That looks like a secret: never store secrets in memory.")
    if topic:
        topic = topic.lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", topic):
            raise ErrorUso("Invalid topic: use [a-z0-9_.-], one word.")
    for x in (by, undo):
        if x and len(x) > MAX_EXTRA:
            raise ErrorUso(f"--by and --undo are limited to {MAX_EXTRA} characters.")
    if type == "decision":
        if not by:
            raise ErrorUso("A decision is made by a human: pass --by <human name>. The agent only records it.")
        if by.lower() in NO_HUMANOS or by.lower() == agente:
            raise ErrorUso(f"--by must be a human name, not {by!r}.")
        text += f" (by {by})"
    elif type == "agreed":
        if not undo:
            raise ErrorUso("An agreed entry is a reversible choice: pass --undo <how to undo it>.")
        text += f" (undo: {undo})"
    archivo = raiz() / ".omen-memoria" / "MEMORY.md"
    with _Candado():
        previas = [e for e in _leer(archivo) if topic and e["topic"] == topic and e["type"] in ("decision", "agreed")]
        if type == "agreed" and any(e["type"] == "decision" for e in previas):
            raise ErrorUso(f"Topic {topic!r} already has a human decision: an agreed entry cannot replace it; "
                           "ask the human.")
        ig = archivo.parent / ".gitignore"  # marks are per machine: keep them out of git
        if not ig.exists():
            ig.write_text("seen/\n.lock\n")
        linea = " · ".join([datetime.now().strftime("%Y-%m-%d %H:%M"), agente, type, text] +
                           ([source] if source else []) + ([f"topic: {topic}"] if topic else []))
        with open(archivo, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    return linea + (f"\nReplaces: {previas[-1]['text']}" if type in ("decision", "agreed") and previas else "")


def _recortar(lineas, tope):
    """Keep the newest lines that fit in `tope` bytes; return (kept, omitted)."""
    usado, dentro = 0, []
    for l in reversed(lineas):
        usado += len(l.encode()) + 1
        if usado > tope:
            break
        dentro.append(l)
    return dentro[::-1], len(lineas) - len(dentro)


def vigentes_txt():
    archivo = raiz() / ".omen-memoria" / "MEMORY.md"
    vig = [_fmt(e) for e in _vigentes(_leer(archivo))]
    return "\n".join(vig) if vig else "No current decisions."


def nuevo(agent=None):
    """Current decisions + what other agents wrote since this agent's last start. Moves the mark."""
    agente = _agente(agent)
    archivo = raiz() / ".omen-memoria" / "MEMORY.md"
    if not archivo.exists():
        return ""
    with _Candado():
        entradas = _leer(archivo)
        total = len(archivo.read_text(encoding="utf-8").splitlines())
        marca = archivo.parent / "seen" / agente
        try:
            visto = int(marca.read_text())
        except (OSError, ValueError):
            visto = 0
        marca.parent.mkdir(exist_ok=True)
        marca.write_text(str(total))
    if not entradas:
        return ""
    nuevas = [e for e in entradas if e["n"] > (visto if visto <= total else 0) and e["agent"] != agente]
    vigentes, ids = _vigentes(entradas), {e["n"] for e in nuevas}
    vig, om_v = _recortar([f"- {'NEW ' if e['n'] in ids else ''}{_fmt(e)}" for e in vigentes], 1800)
    otras = [e for e in nuevas if e not in vigentes]  # new decisions are already above, marked NEW
    nue, om_n = _recortar([f"- {_fmt(e)}" for e in otras], 1800)
    salida = [f"OMEN memory ({raiz().name}) · you are {agente}", f"Current decisions ({len(vig) + om_v}):"] + vig
    if om_v:
        salida.append(f"  ({om_v} older omitted: use memory_current or `memoria.py current`)")
    salida.append(f"New since your last session ({len(nuevas)}"
                  + (f", {len(nuevas) - len(otras)} marked NEW above" if len(otras) < len(nuevas) else "") + "):")
    salida += nue
    if om_n:
        salida.append(f"  ({om_n} older omitted: use memory_search)")
    return "\n".join(salida)


def _norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))


def buscar(query):
    palabras = _norm(query).split()
    if not palabras:
        raise ErrorUso("Empty search.")
    hits = [e for e in _leer(raiz() / ".omen-memoria" / "MEMORY.md") if all(w in _norm(e["raw"]) for w in palabras)]
    if not hits:
        return "No matches."
    lineas, omitidas = _recortar([f"#{e['n']} {_fmt(e)}" for e in hits], MAX_SALIDA)
    return "\n".join(lineas + ([f"({omitidas} older matches omitted: narrow the search)"] if omitidas else []))


# name -> (function, description, properties, required)
_S = lambda d: {"type": "string", "description": d}  # noqa: E731
_AG = _S("Agent name [a-z0-9_-]. Default: $OMEN_MEMORIA_AGENT or 'claude'.")
HERRAMIENTAS = {
    "memory_write": (escribir,
        "Append one entry to the team memory file. Use after a human decides something (type decision, needs by), "
        "when you make a reversible choice (agreed, needs undo), at the end of a session (done: what and where to "
        "see it), or for a lasting lesson (lesson). A newer decision/agreed on the same topic replaces the old one. "
        "Max 280 characters: put detail in a file and cite it in source. Never store secrets.",
        {"type": {"type": "string", "enum": list(TIPOS), "description": "Entry type."},
         "text": _S("The entry, max 280 characters."), "source": _S("Optional file or link with the detail."),
         "topic": _S("Optional topic, one word; same topic = replaces the older decision."),
         "by": _S("Human who decided (required for decision)."), "undo": _S("How to undo it (required for agreed)."),
         "agent": _AG}, ["type", "text"]),
    "memory_search": (buscar,
        "Search the team memory (accent- and case-insensitive, all words must match). Use before starting work on "
        "something that may already have been decided, tried or learned.",
        {"query": _S("Words to look for.")}, ["query"]),
    "memory_current": (vigentes_txt,
        "List the current decisions: per topic only the newest decision/agreed entry.", {}, []),
    "memory_new": (nuevo,
        "Show the current decisions and what OTHER agents wrote since this agent's last session, then mark them as "
        "seen. The SessionStart hook does this automatically; call it if the hook did not run.",
        {"agent": _AG}, []),
}


# ---------------------------------------------------------------- MCP stdio
def _herramientas_mcp():
    return [{"name": n, "title": n.replace("_", " ").title(), "description": d,
             "inputSchema": {"type": "object", "properties": p, "required": r},
             "annotations": {"readOnlyHint": n in ("memory_search", "memory_current"), "destructiveHint": False,
                             "openWorldHint": False}}
            for n, (_, d, p, r) in HERRAMIENTAS.items()]


def manejar(msg):
    """Handle one JSON-RPC message. Returns the response dict, or None for notifications."""
    if not isinstance(msg, dict):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}
    metodo, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if "id" not in msg:
        return None

    def ok(resultado):
        return {"jsonrpc": "2.0", "id": mid, "result": resultado}

    def err(codigo, mensaje):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": codigo, "message": mensaje}}

    if metodo == "initialize":
        return ok({"protocolVersion": params.get("protocolVersion") or "2025-06-18",
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": NOMBRE, "version": VERSION},
                   "instructions": "Shared team memory in .omen-memoria/MEMORY.md. Search before re-deciding; write "
                                   "decisions, reversible choices, session closures and lessons. Never secrets."})
    if metodo == "ping":
        return ok({})
    if metodo == "tools/list":
        return ok({"tools": _herramientas_mcp()})
    if metodo == "tools/call":
        nombre = params.get("name")
        if nombre not in HERRAMIENTAS:
            return err(-32602, f"Unknown tool: {nombre}")
        fn, _, props, _ = HERRAMIENTAS[nombre]
        args = {k: v for k, v in (params.get("arguments") or {}).items() if k in props and v not in (None, "")}
        try:
            texto, es_error = fn(**args) or "(empty)", False
        except ErrorUso as e:
            texto, es_error = f"Error: {e}", True
        except Exception as e:  # noqa: BLE001 - reported to the client, never kills the server
            texto, es_error = f"Internal failure: {e!r}", True
        return ok({"content": [{"type": "text", "text": texto}], "isError": es_error})
    return err(-32601, f"Method not found: {metodo}")


def servir_mcp():
    for linea in sys.stdin.buffer:
        linea = linea.strip()
        if not linea:
            continue
        try:
            resp = manejar(json.loads(linea))
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


# ---------------------------------------------------------------- CLI
def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="memoria.py", description="OMEN Memoria: shared team memory.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write", help="Append an entry")
    w.add_argument("type", choices=TIPOS)
    w.add_argument("text")
    for k in ("source", "topic", "by", "undo", "agent"):
        w.add_argument(f"--{k}")
    sub.add_parser("start", help="Current decisions + new since your last session").add_argument("--agent")
    sub.add_parser("search", help="Search entries").add_argument("words", nargs="+")
    sub.add_parser("current", help="Current decisions")
    sub.add_parser("mcp", help="MCP server over stdio")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "mcp":
            servir_mcp()
            return 0
        if a.cmd == "write":
            salida = escribir(a.type, a.text, a.source, a.topic, a.by, a.undo, a.agent)
        elif a.cmd == "start":
            salida = nuevo(a.agent)
        elif a.cmd == "search":
            salida = buscar(" ".join(a.words))
        else:
            salida = vigentes_txt()
    except ErrorUso as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if salida:
        print(salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
