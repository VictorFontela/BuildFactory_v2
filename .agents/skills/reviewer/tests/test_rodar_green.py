"""rodar_green.py: aceita o green só com testes do passo passando, testes intocados, diretórios e suíte sem falha nova."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rodar_green.py"
SUITE = f"{sys.executable} -m pytest -q -p no:cacheprovider --junitxml=.tmp/suite.xml"


def git(raiz, *args):
    return subprocess.run(["git", "-C", str(raiz), *args], check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, arquivos, msg="feat"):
    for nome, txt in arquivos.items():
        (repo / nome).parent.mkdir(parents=True, exist_ok=True)
        (repo / nome).write_text(txt)
    git(repo, "add", *arquivos)
    git(repo, "commit", "-qm", msg)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / ".gitignore").write_text(".tmp/\nbase.json\nred.json\nrel.json\n__pycache__/\n")
    commit(tmp_path, {
        ".gitignore": (tmp_path / ".gitignore").read_text(),
        "api/__init__.py": "", "api/tarefas.py": "def concluir(i):\n    raise NotImplementedError\n",
        "api/velho.py": "def soma(a, b):\n    return a + b\n",
        "tests/__init__.py": "",
        "tests/test_velho.py": "from api.velho import soma\n\ndef test_soma():\n    assert soma(1, 2) == 3\n",
        "tests/test_quebrado.py": "def test_ja_falhava():\n    assert False\n",
    }, "base")
    return tmp_path


def baseline(repo):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--gravar-baseline", "--suite", SUITE,
                           "--junit", ".tmp/suite.xml", "--baseline", str(repo / "base.json")], capture_output=True, text=True)


def red(repo):
    commit(repo, {"tests/test_tarefas.py": "from api.tarefas import concluir\n\ndef test_concluir():\n    assert concluir(1) is True\n"},
           "test: red")
    ev = {"tipo": "testes_red", "passo": 1, "arquivos": ["tests/test_tarefas.py"], "comando": "pytest",
          "falhas": ["test_concluir: NotImplementedError"], "commit": git(repo, "rev-parse", "--short=12", "HEAD")}
    (repo / "red.json").write_text(json.dumps(ev))


def rodar(repo, diretorios=("api/",), com_base=True):
    args = [sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--testes-red", str(repo / "red.json"),
            "--diretorios", *diretorios, "--suite", SUITE, "--junit", ".tmp/suite.xml", "--saida", str(repo / "rel.json")]
    if com_base:
        args += ["--baseline", str(repo / "base.json")]
    r = subprocess.run(args, capture_output=True, text=True)
    rel = json.loads((repo / "rel.json").read_text()) if (repo / "rel.json").exists() else None
    return r.returncode, r.stdout + r.stderr, rel


CERTO = {"api/tarefas.py": "def concluir(i):\n    return True\n"}


def test_baseline_guarda_quem_ja_falhava(repo):
    r = baseline(repo)
    assert r.returncode == 0, r.stderr
    b = json.loads((repo / "base.json").read_text())
    assert b["falhando"] == ["tests.test_quebrado::test_ja_falhava"]
    assert b["total"] == 2 and b["commit"] == git(repo, "rev-parse", "--short=12", "HEAD")


def test_green_certo_e_aceito_mesmo_com_falha_antiga(repo):
    baseline(repo)
    red(repo)
    commit(repo, CERTO)
    cod, msg, rel = rodar(repo)
    assert cod == 0, msg
    assert rel["ok"] and rel["testes_do_passo"]["total"] == 1 and rel["suite"]["novas_falhas"] == []
    assert rel["suite"]["falhas_da_linha_de_base"] == 1


def test_teste_do_passo_falhando_reprova(repo):
    baseline(repo)
    red(repo)
    commit(repo, {"api/tarefas.py": "def concluir(i):\n    return False\n"})
    cod, _, rel = rodar(repo)
    assert cod == 1 and not rel["ok"] and rel["testes_do_passo"]["falhas"]
    assert any("testes do passo" in m for m in rel["motivos"])


def test_teste_alterado_reprova_mesmo_passando(repo):
    baseline(repo)
    red(repo)
    commit(repo, {**CERTO, "tests/test_tarefas.py": "def test_concluir():\n    assert True\n"})
    cod, _, rel = rodar(repo, diretorios=("api/", "tests/"))
    assert cod == 1 and rel["testes_mexidos"] == ["tests/test_tarefas.py"] and not rel["testes_intocados"]


def test_arquivo_fora_dos_diretorios_reprova(repo):
    baseline(repo)
    red(repo)
    commit(repo, {**CERTO, "web/tela.js": "x\n"})
    cod, _, rel = rodar(repo)
    assert cod == 1 and rel["fora_dos_diretorios"] == ["web/tela.js"]


def test_prefixo_parecido_nao_conta_como_dentro(repo):
    baseline(repo)
    red(repo)
    commit(repo, {**CERTO, "api-legada/x.py": "x = 1\n"})
    cod, _, rel = rodar(repo)
    assert cod == 1 and rel["fora_dos_diretorios"] == ["api-legada/x.py"]


def test_bytecode_velho_nao_esconde_falha_nova(repo):
    import os
    baseline(repo)
    red(repo)
    velho = repo / "api/velho.py"
    st = velho.stat()
    commit(repo, {**CERTO, "api/velho.py": "def soma(a, b):\n    return a - b\n"})
    os.utime(velho, ns=(st.st_atime_ns, st.st_mtime_ns))
    cod, _, rel = rodar(repo)
    assert cod == 1 and "test_soma" in rel["suite"]["novas_falhas"][0]


def test_quebrar_teste_antigo_reprova_como_falha_nova(repo):
    baseline(repo)
    red(repo)
    commit(repo, {**CERTO, "api/velho.py": "def soma(a, b):\n    return a - b\n"})
    cod, _, rel = rodar(repo)
    assert cod == 1 and len(rel["suite"]["novas_falhas"]) == 1 and "test_soma" in rel["suite"]["novas_falhas"][0]


def test_mudanca_sem_commit_reprova(repo):
    baseline(repo)
    red(repo)
    commit(repo, CERTO)
    (repo / "api" / "rascunho.py").write_text("y = 2\n")
    cod, _, rel = rodar(repo)
    assert cod == 1 and rel["mudancas_sem_commit"]


def test_sem_baseline_falha_antiga_conta_como_nova_e_avisa(repo):
    red(repo)
    commit(repo, CERTO)
    cod, _, rel = rodar(repo, com_base=False)
    assert cod == 1 and "aviso" in rel and len(rel["suite"]["novas_falhas"]) == 1


def test_arquivo_do_passo_sem_caso_reprova(repo):
    baseline(repo)
    red(repo)
    commit(repo, CERTO)
    ev = json.loads((repo / "red.json").read_text())
    ev["arquivos"].append("tests/test_sumiu.py")
    (repo / "red.json").write_text(json.dumps(ev))
    cod, _, rel = rodar(repo)
    assert cod == 1 and rel["testes_do_passo"]["arquivos_sem_caso"] == ["tests/test_sumiu.py"]


def test_suite_que_nao_grava_relatorio_e_uso_errado(repo):
    red(repo)
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--testes-red", str(repo / "red.json"),
                        "--diretorios", "api/", "--suite", "true", "--junit", ".tmp/suite.xml"], capture_output=True, text=True)
    assert r.returncode == 2 and "não rodou" in r.stderr


def test_arquivo_de_teste_no_lugar_do_evento_e_uso_errado(repo):
    red(repo)
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--testes-red", str(repo / "tests/test_tarefas.py"),
                        "--diretorios", "api/", "--suite", SUITE, "--junit", ".tmp/suite.xml"], capture_output=True, text=True)
    assert r.returncode == 2 and "espera o arquivo do evento testes_red" in r.stderr


@pytest.mark.parametrize("args", [[], ["--suite", "x", "--junit", "y"], ["--gravar-baseline", "--suite", "x", "--junit", "y"]])
def test_argumentos_faltando_saem_com_2(args):
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True)
    assert r.returncode == 2


def test_relatorio_velho_nao_conta_como_suite_rodada(repo):
    red(repo)
    commit(repo, CERTO)
    (repo / ".tmp").mkdir()
    (repo / ".tmp" / "suite.xml").write_text('<testsuite><testcase classname="tests.test_tarefas" name="test_concluir"/></testsuite>')
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--testes-red", str(repo / "red.json"),
                        "--diretorios", "api/", "--suite", "true", "--junit", ".tmp/suite.xml"], capture_output=True, text=True)
    assert r.returncode == 2 and "não rodou" in r.stderr


def test_sem_diretorios_e_uso_errado(repo):
    red(repo)
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--testes-red", str(repo / "red.json"),
                        "--suite", SUITE, "--junit", ".tmp/suite.xml"], capture_output=True, text=True)
    assert r.returncode == 2


def projeto(repo):
    (repo / ".agents").mkdir(exist_ok=True)
    (repo / ".agents" / "projeto.json").write_text(json.dumps({"suite": SUITE, "junit": ".tmp/suite.xml"}))


def test_modo_da_entrada_usa_projeto_spec_e_baseline_da_capacidade(repo):
    projeto(repo)
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--gravar-baseline", "--capacidade", "todo"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (repo / ".agents/state/todo/baseline-suite.json").is_file()
    red(repo)
    commit(repo, CERTO)
    e = {"capacidade": "todo", "passo": 1, "spec": {"id": 1, "diretorios": ["api/"]},
         "testes_red": json.loads((repo / "red.json").read_text()), "builds": []}
    (repo / "entrada.json").write_text(json.dumps(e))
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--testes-red", str(repo / "entrada.json")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    rel = json.loads(r.stdout)
    assert rel["suite"]["falhas_da_linha_de_base"] == 1 and "aviso" not in rel


def test_diretorios_da_spec_valem(repo):
    projeto(repo)
    red(repo)
    commit(repo, CERTO)
    e = {"capacidade": "todo", "passo": 1, "spec": {"id": 1, "diretorios": ["web/"]},
         "testes_red": json.loads((repo / "red.json").read_text())}
    (repo / "entrada.json").write_text(json.dumps(e))
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--testes-red", str(repo / "entrada.json")],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "api/tarefas.py" in json.loads(r.stdout)["fora_dos_diretorios"]


def test_sem_configuracao_da_suite_e_uso_errado(repo):
    red(repo)
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--testes-red", str(repo / "red.json"),
                        "--diretorios", "api/"], capture_output=True, text=True)
    assert r.returncode == 2 and "projeto.json" in r.stderr


def test_suite_com_dois_relatorios_soma_os_dois(repo):
    baseline(repo)
    red(repo)
    commit(repo, CERTO)
    (repo / ".tmp").mkdir(exist_ok=True)
    extra = '<testsuite><testcase classname="web/a.test.mjs" name="tela" file="web/a.test.mjs"><failure message="x"/></testcase></testsuite>'
    suite = f"{SUITE} ; printf '%s' '{extra}' > .tmp/web.xml"
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--testes-red", str(repo / "red.json"),
                        "--diretorios", "api/", "--suite", suite, "--junit", ".tmp/suite.xml", ".tmp/web.xml",
                        "--baseline", str(repo / "base.json")], capture_output=True, text=True)
    rel = json.loads(r.stdout)
    assert r.returncode == 1 and rel["suite"]["total"] == 4 and "web/a.test.mjs::tela" in rel["suite"]["novas_falhas"]
