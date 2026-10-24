import importlib.util
import json
import multiprocessing
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "team-memory" / "scripts" / "memoria.py"
spec = importlib.util.spec_from_file_location("memoria", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

LINEA = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} · [a-z0-9_-]+ · \w+ · .+")


def _escritor(agente, n):
    for i in range(n):
        m.escribir("done", f"{agente} line {i}", agent=agente)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / ".git").mkdir()  # stops the climb at the temp dir
        self._env = {k: os.environ.pop(k, None) for k in ("OMEN_MEMORIA_AGENT", "OMEN_MEMORIA_DIR")}
        os.environ["OMEN_MEMORIA_DIR"] = self.tmp.name
        self.mem = self.dir / ".omen-memoria" / "MEMORY.md"

    def tearDown(self):
        for k, v in self._env.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
        self.tmp.cleanup()

    def lineas(self):
        return self.mem.read_text(encoding="utf-8").splitlines()


class TestEscribir(Base):
    def test_formato_de_linea(self):
        m.escribir("done", "Shipped the thing", source="docs/x.md", topic="Ship", agent="ana")
        m.escribir("lesson", "Plain one", agent="ana")
        a, b = self.lineas()
        self.assertRegex(a, LINEA)
        self.assertTrue(a.endswith(" · ana · done · Shipped the thing · docs/x.md · topic: ship"), a)
        self.assertTrue(b.endswith(" · ana · lesson · Plain one"), b)

    def test_280(self):
        m.escribir("done", "x" * 280)
        with self.assertRaisesRegex(m.ErrorUso, "file"):
            m.escribir("done", "x" * 281)
        self.assertEqual(len(self.lineas()), 1)

    def test_decision_exige_by_humano(self):
        with self.assertRaisesRegex(m.ErrorUso, "--by"):
            m.escribir("decision", "Use Postgres")
        with self.assertRaises(m.ErrorUso):
            m.escribir("decision", "Use Postgres", by="claude")
        m.escribir("decision", "Use Postgres", by="Enrique")
        self.assertIn("Use Postgres (by Enrique)", self.lineas()[0])

    def test_agreed_exige_undo(self):
        with self.assertRaisesRegex(m.ErrorUso, "--undo"):
            m.escribir("agreed", "Rename module")
        m.escribir("agreed", "Rename module", undo="git revert abc")
        self.assertIn("(undo: git revert abc)", self.lineas()[0])

    def test_nombre_de_agente(self):
        with self.assertRaises(m.ErrorUso):
            m.escribir("done", "x", agent="Bad Name")

    def test_agente_por_entorno(self):
        os.environ["OMEN_MEMORIA_AGENT"] = "ayanami"
        m.escribir("done", "x")
        self.assertIn(" · ayanami · ", self.lineas()[0])

    def test_guardia_de_secretos(self):
        for malo in ("key sk-abcdefghijklmnop1234", "ghp_" + "a" * 30, "github_pat_" + "b" * 30, "AKIA" + "A" * 16,
                     "xoxb-1234567890-abc", "-----BEGIN PRIVATE KEY-----", "password=hunter2", "API_KEY = abc123",
                     "token=xyz"):
            with self.assertRaisesRegex(m.ErrorUso, "never store secrets", msg=malo):
                m.escribir("done", malo)
        m.escribir("done", "Rotated the token policy, see docs")
        self.assertEqual(len(self.lineas()), 1)

    def test_separador_en_texto(self):
        m.escribir("done", "a · b")
        self.assertEqual(len(m._leer(self.mem)), 1)
        self.assertEqual(m._leer(self.mem)[0]["text"], "a - b")


class TestVigentes(Base):
    def test_topic_reemplaza(self):
        m.escribir("decision", "Use MySQL", by="Ana", topic="db")
        out = m.escribir("decision", "Use Postgres", by="Ana", topic="db")
        self.assertIn("Replaces: Use MySQL", out)
        vig = [e["text"] for e in m._vigentes(m._leer(self.mem))]
        self.assertEqual(vig, ["Use Postgres (by Ana)"])

    def test_agreed_no_reemplaza_decision(self):
        m.escribir("decision", "Use Postgres", by="Ana", topic="db")
        with self.assertRaisesRegex(m.ErrorUso, "ask the human"):
            m.escribir("agreed", "Use SQLite", undo="revert", topic="db")
        self.assertEqual(len(self.lineas()), 1)

    def test_agreed_reemplaza_agreed_y_decision_reemplaza_agreed(self):
        m.escribir("agreed", "A", undo="u", topic="t")
        m.escribir("agreed", "B", undo="u", topic="t")
        m.escribir("decision", "C", by="Ana", topic="t")
        self.assertEqual([e["text"] for e in m._vigentes(m._leer(self.mem))], ["C (by Ana)"])

    def test_vigentes_sin_topic_todas_y_otros_tipos_no(self):
        m.escribir("decision", "One", by="Ana")
        m.escribir("agreed", "Two", undo="u")
        m.escribir("done", "Three")
        m.escribir("proposed", "Four", topic="x")
        self.assertEqual(len(m._vigentes(m._leer(self.mem))), 2)
        self.assertNotIn("Three", m.vigentes_txt())


class TestNuevo(Base):
    def test_solo_de_otros_y_marca_avanza(self):
        m.escribir("done", "mine 1", agent="ana")
        m.escribir("done", "theirs 1", agent="beto")
        out = m.nuevo("ana")
        self.assertIn("New since your last session (1)", out)
        self.assertIn("theirs 1", out)
        self.assertNotIn("mine 1", out)
        self.assertEqual((self.dir / ".omen-memoria" / "seen" / "ana").read_text(), "2")
        self.assertIn("New since your last session (0)", m.nuevo("ana"))
        m.escribir("done", "theirs 2", agent="beto")
        out = m.nuevo("ana")
        self.assertIn("(1)", out)
        self.assertIn("theirs 2", out)
        self.assertNotIn("theirs 1", out)

    def test_primera_vez_ve_todo_lo_ajeno_y_vigentes(self):
        m.escribir("decision", "Use Postgres", by="Ana", topic="db", agent="beto")
        out = m.nuevo("ana")
        self.assertIn("Current decisions (1):", out)
        self.assertIn("(1):\n- ", out)

    def test_salida_acotada(self):
        for i in range(60):
            m.escribir("done", f"entry number {i} " + "y" * 200, agent="beto")
        out = m.nuevo("ana")
        self.assertLessEqual(len(out.encode()), 4096)
        self.assertRegex(out, r"\(\d+ older omitted")
        self.assertIn("entry number 59", out)


class TestBuscar(Base):
    def test_sin_acentos_ni_mayusculas_y_todas_las_palabras(self):
        m.escribir("lesson", "La conexión a Postgres falla sin SSL")
        m.escribir("lesson", "Conexion lenta en Redis")
        self.assertEqual(len(m.buscar("CONEXION postgres").splitlines()), 1)
        self.assertEqual(len(m.buscar("conexión").splitlines()), 2)
        self.assertEqual(m.buscar("nada"), "No matches.")


class TestConcurrencia(Base):
    def test_dos_procesos_100_lineas(self):
        ps = [multiprocessing.Process(target=_escritor, args=(a, 50)) for a in ("ana", "beto")]
        [p.start() for p in ps]
        [p.join() for p in ps]
        ls = self.lineas()
        self.assertEqual(len(ls), 100)
        self.assertTrue(all(LINEA.match(l) for l in ls))
        for a in ("ana", "beto"):
            self.assertEqual(sum(f" · {a} · " in l for l in ls), 50)


class TestCLIyMCP(Base):
    def correr(self, *args, entrada=None, cwd=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=entrada, capture_output=True, text=True,
                              cwd=cwd or self.tmp.name, env=dict(os.environ), timeout=30)

    def test_hook_sin_memoria_no_imprime(self):
        r = self.correr("start")
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        self.assertFalse((self.dir / ".omen-memoria").exists())

    def test_hook_con_memoria_imprime(self):
        self.correr("write", "decision", "Use Postgres", "--by", "Ana", "--agent", "beto")
        r = self.correr("start", "--agent", "ana")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Use Postgres", r.stdout)

    def test_cli_error_claro(self):
        r = self.correr("write", "decision", "x")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--by", r.stderr)

    def test_cli_search_y_current(self):
        self.correr("write", "decision", "Use Postgres", "--by", "Ana", "--topic", "db")
        self.assertIn("Use Postgres", self.correr("search", "postgres").stdout)
        self.assertIn("Use Postgres", self.correr("current").stdout)

    def test_mcp_stdio(self):
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "memory_write", "arguments": {
                "type": "decision", "text": "Use Postgres", "by": "Ana", "topic": "db", "agent": "beto"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "memory_write", "arguments": {
                "type": "decision", "text": "no by"}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "memory_search",
                                                                             "arguments": {"query": "postgres"}}},
            {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "memory_current", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "memory_new",
                                                                             "arguments": {"agent": "ana"}}},
        ]
        r = self.correr("mcp", entrada="\n".join(json.dumps(x) for x in msgs) + "\n")
        resp = {x["id"]: x for x in map(json.loads, r.stdout.splitlines())}
        self.assertEqual(sorted(resp), [1, 2, 3, 4, 5, 6, 7])  # the notification got no answer
        self.assertEqual(resp[1]["result"]["serverInfo"]["name"], "omen-memoria")
        nombres = {t["name"] for t in resp[2]["result"]["tools"]}
        self.assertEqual(nombres, {"memory_write", "memory_search", "memory_current", "memory_new"})
        self.assertFalse(resp[3]["result"]["isError"])
        self.assertTrue(resp[4]["result"]["isError"])
        for i in (5, 6, 7):
            self.assertIn("Use Postgres", resp[i]["result"]["content"][0]["text"])
        self.assertIn("(1)", resp[7]["result"]["content"][0]["text"])


class TestPlugin(unittest.TestCase):
    def test_hooks_y_mcp_apuntan_al_script(self):
        raiz = SCRIPT.parents[3]
        for rel in ("hooks/hooks.json", ".mcp.json"):
            txt = (raiz / rel).read_text()
            json.loads(txt)
            self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/team-memory/scripts/memoria.py", txt)


if __name__ == "__main__":
    unittest.main()
