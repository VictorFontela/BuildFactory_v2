"""junit.py: lê os relatórios e acha os casos de cada arquivo de teste."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from junit import RelatorioInvalido, caso_do_arquivo, id_do_caso, ler_junit, ler_varios  # noqa: E402

REPORTER = Path(__file__).resolve().parents[1] / "reporters" / "junit-node.mjs"


def test_pytest_sem_file_acha_pelo_classname(tmp_path):
    (tmp_path / "r.xml").write_text('<testsuite><testcase classname="api.tests.test_x.TestA" name="t1"/>'
                                    '<testcase classname="api.tests.test_xy" name="t2"><failure message="m"/></testcase></testsuite>')
    c = ler_junit(tmp_path / "r.xml")
    assert [caso_do_arquivo(x, "api/tests/test_x.py") for x in c] == [True, False]
    assert c[1]["tipo"] == "falha" and id_do_caso(c[1]) == "api.tests.test_xy::t2"


def test_classname_com_caminho_como_o_vitest(tmp_path):
    (tmp_path / "r.xml").write_text('<testsuite><testcase classname="web/a.test.ts" name="t"/></testsuite>')
    assert caso_do_arquivo(ler_junit(tmp_path / "r.xml")[0], "web/a.test.ts")


def test_varios_relatorios_somam_e_um_faltando_e_invalido(tmp_path):
    (tmp_path / "a.xml").write_text('<testsuite><testcase classname="a" name="1"/></testsuite>')
    (tmp_path / "b.xml").write_text('<testsuite><testcase classname="b" name="2"/></testsuite>')
    assert len(ler_varios([tmp_path / "a.xml", tmp_path / "b.xml"])) == 2
    with pytest.raises(RelatorioInvalido):
        ler_varios([tmp_path / "a.xml", tmp_path / "c.xml"])


@pytest.mark.skipif(subprocess.run(["node", "--version"], capture_output=True).returncode != 0, reason="sem node")
def test_reporter_do_node_separa_falha_de_erro_e_grava_o_arquivo(tmp_path):
    (tmp_path / "web").mkdir()
    (tmp_path / "web/m.mjs").write_text("export function f() { throw new Error('não implementado') }\n")
    (tmp_path / "web/a.test.mjs").write_text(
        'import test from "node:test";\nimport assert from "node:assert/strict";\nimport { f } from "./m.mjs";\n'
        'test("assert", () => assert.equal(1, 2));\ntest("passa", () => {});\ntest("excecao", () => f());\n')
    (tmp_path / "web/b.test.mjs").write_text('import { nao_existe } from "./m.mjs";\n')
    subprocess.run(["node", "--test", f"--test-reporter={REPORTER}", "--test-reporter-destination=r.xml",
                    "web/a.test.mjs", "web/b.test.mjs"], cwd=tmp_path, capture_output=True)
    c = {x["nome"]: x for x in ler_junit(tmp_path / "r.xml")}
    assert c["assert"]["tipo"] == "falha" and c["excecao"]["tipo"] == "falha" and c["passa"]["tipo"] == "ok"
    assert c["web/b.test.mjs"]["tipo"] == "erro"
    assert all(caso_do_arquivo(c[n], "web/a.test.mjs") for n in ("assert", "passa", "excecao"))
