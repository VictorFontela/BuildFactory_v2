"""E4a: rodar_red.py aceita só o red pelo motivo certo, em repositórios git temporários."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rodar_red.py"
JUNIT = "relatorio/red.xml"

FALHA = "def test_concluir():\n    assert 404 == 200\n\ndef test_filtrar():\n    assert [] == ['x']\n"
PASSA = "def test_ok():\n    assert 1 == 1\n"
IMPORT = "from app.tarefas import concluir\n\ndef test_concluir():\n    assert concluir(1)\n"
SINTAXE = "def test_quebrado(:\n    assert True\n"
VAZIO = "VALOR = 1\n"


def git(raiz, *args):
    subprocess.run(["git", "-C", str(raiz), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "__init__.py").write_text("")
    (tmp_path / ".gitignore").write_text("relatorio/\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def escrever(repo, arquivos, commit=True, extra=None):
    for nome, txt in arquivos.items():
        (repo / nome).write_text(txt)
    if extra:
        for nome, txt in extra.items():
            (repo / nome).write_text(txt)
    if commit:
        git(repo, "add", *arquivos, *(extra or {}))
        git(repo, "commit", "-qm", "test: red")


def rodar(repo, arquivos):
    cmd = f"{sys.executable} -m pytest -q -p no:cacheprovider {' '.join(arquivos)} --junitxml={JUNIT}"
    ev = repo / "saida.json"
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--passo", "1", "--comando", cmd,
                        "--junit", JUNIT, "--arquivos", *arquivos, "--evento", str(ev)],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr, (json.loads(ev.read_text()) if ev.exists() else None)


def test_falha_por_assert_e_aceita_e_gera_o_evento(repo):
    escrever(repo, {"tests/test_status.py": FALHA})
    cod, msg, ev = rodar(repo, ["tests/test_status.py"])
    assert cod == 0, msg
    assert ev["tipo"] == "testes_red" and len(ev["falhas"]) == 2
    assert ev["falhas"][0].startswith("test_concluir: ")
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert ev["commit"] == head


def test_erro_de_import_e_recusado(repo):
    escrever(repo, {"tests/test_status.py": IMPORT})
    cod, msg, ev = rodar(repo, ["tests/test_status.py"])
    assert cod == 1 and "erro(s) antes de o teste rodar" in msg and ev is None


def test_erro_de_sintaxe_e_recusado(repo):
    escrever(repo, {"tests/test_status.py": SINTAXE})
    cod, msg, _ = rodar(repo, ["tests/test_status.py"])
    assert cod == 1 and "erro(s) antes de o teste rodar" in msg


def test_testes_que_ja_passam_sao_recusados(repo):
    escrever(repo, {"tests/test_status.py": PASSA})
    cod, msg, _ = rodar(repo, ["tests/test_status.py"])
    assert cod == 1 and "já passam" in msg


def test_nenhum_teste_e_recusado(repo):
    escrever(repo, {"tests/test_status.py": VAZIO})
    cod, msg, _ = rodar(repo, ["tests/test_status.py"])
    assert cod == 1 and "nenhum teste" in msg


def test_arquivo_listado_sem_caso_e_recusado(repo):
    escrever(repo, {"tests/test_status.py": FALHA, "tests/test_vazio.py": VAZIO})
    cod, msg, _ = rodar(repo, ["tests/test_status.py", "tests/test_vazio.py"])
    assert cod == 1 and "sem nenhum caso" in msg and "tests/test_vazio.py" in msg


def test_commit_com_arquivo_que_nao_e_teste_e_recusado(repo):
    escrever(repo, {"tests/test_status.py": FALHA}, extra={"app/tarefas.py": "def concluir(i):\n    return True\n"})
    cod, msg, _ = rodar(repo, ["tests/test_status.py"])
    assert cod == 1 and "app/tarefas.py" in msg


def test_teste_fora_do_commit_e_recusado(repo):
    escrever(repo, {"tests/test_status.py": FALHA}, commit=False)
    cod, msg, _ = rodar(repo, ["tests/test_status.py"])
    assert cod == 1 and "fora do último commit" in msg


def test_teste_alterado_depois_do_commit_e_recusado(repo):
    escrever(repo, {"tests/test_status.py": FALHA})
    (repo / "tests" / "test_status.py").write_text(FALHA + "\ndef test_novo():\n    assert False\n")
    cod, msg, _ = rodar(repo, ["tests/test_status.py"])
    assert cod == 1 and "mudança fora do commit" in msg


def test_relatorio_antigo_nao_vale(repo):
    escrever(repo, {"tests/test_status.py": FALHA})
    assert rodar(repo, ["tests/test_status.py"])[0] == 0
    ev = repo / "saida.json"
    cmd_sem_junit = f"{sys.executable} -m pytest -q -p no:cacheprovider tests/test_status.py"
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--passo", "1", "--comando", cmd_sem_junit,
                        "--junit", JUNIT, "--arquivos", "tests/test_status.py", "--evento", str(ev)], capture_output=True, text=True)
    assert r.returncode == 1 and "não gravou o relatório" in r.stderr


def test_uso_errado(repo):
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--passo", "1"], capture_output=True, text=True)
    assert r.returncode == 2


def test_relatorio_no_formato_do_jest_com_atributo_file(tmp_path):
    sys.path.insert(0, str(SCRIPT.parent))
    import rodar_red
    xml = tmp_path / "jest.xml"
    xml.write_text('<testsuites><testsuite name="Lista"><testcase classname="Lista filtra" name="mostra só concluídas" '
                   'file="web/src/tarefas/Lista.test.tsx"><failure message="expected 3, received 0"/></testcase>'
                   '</testsuite></testsuites>')
    casos = rodar_red.ler_varios([xml])
    assert casos[0]["tipo"] == "falha" and casos[0]["msg"] == "expected 3, received 0"
    assert rodar_red.caso_do_arquivo(casos[0], "web/src/tarefas/Lista.test.tsx")
    assert not rodar_red.caso_do_arquivo(casos[0], "web/src/tarefas/Outra.test.tsx")
