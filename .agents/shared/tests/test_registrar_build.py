"""registrar_build.py: grava o build_pronto a partir do git e recusa build que mexe em teste ou sai dos diretórios."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "registrar_build.py"


def git(raiz, *args):
    return subprocess.run(["git", "-C", str(raiz), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    for d in ("api", "api/tests", "web"):
        (tmp_path / d).mkdir()
    (tmp_path / "api" / "tarefas.py").write_text("def concluir(i):\n    raise NotImplementedError\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "base")
    (tmp_path / "api" / "tests" / "test_t.py").write_text("def test_x():\n    assert False\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "test: red")
    red = {"tipo": "testes_red", "passo": 1, "arquivos": ["api/tests/test_t.py"], "comando": "pytest",
           "falhas": ["test_x: assert False"], "commit": git(tmp_path, "rev-parse", "--short=12", "HEAD")}
    (tmp_path / "red.json").write_text(json.dumps(red))
    return tmp_path


def commit(repo, arquivos, papel="Backend"):
    for nome, txt in arquivos.items():
        (repo / nome).parent.mkdir(parents=True, exist_ok=True)
        (repo / nome).write_text(txt)
    git(repo, "add", *arquivos)
    git(repo, "commit", "-qm", "feat", *(["-m", f"Papel: {papel}"] if papel else []))


def rodar(repo, diretorios=("api/",), passo="1"):
    ev = repo / "build.json"
    if ev.exists():
        ev.unlink()
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--passo", passo, "--builder", "Backend",
                        "--testes-red", str(repo / "red.json"), "--diretorios", *diretorios, "--resumo", "concluir grava a tarefa",
                        "--evento", str(ev)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr, (json.loads(ev.read_text()) if ev.exists() else None)


def test_build_certo_gera_o_evento_do_git(repo):
    commit(repo, {"api/tarefas.py": "def concluir(i):\n    return True\n"})
    cod, msg, ev = rodar(repo)
    assert cod == 0, msg
    assert ev["arquivos"] == ["api/tarefas.py"] and ev["commit"] == git(repo, "rev-parse", "--short=12", "HEAD")


def test_sem_mudanca_e_recusado(repo):
    cod, msg, _ = rodar(repo)
    assert cod == 1 and "nenhuma mudança" in msg


def test_teste_alterado_e_recusado(repo):
    commit(repo, {"api/tarefas.py": "x = 1\n", "api/tests/test_t.py": "def test_x():\n    assert True\n"})
    cod, msg, _ = rodar(repo)
    assert cod == 1 and "arquivos de teste alterados" in msg


def test_fora_dos_diretorios_e_recusado(repo):
    commit(repo, {"api/tarefas.py": "x = 1\n", "web/tela.js": "x\n"})
    cod, msg, _ = rodar(repo)
    assert cod == 1 and "web/tela.js" in msg


def test_prefixo_parecido_nao_conta_como_dentro(repo):
    commit(repo, {"api-legada/x.py": "x = 1\n"})
    cod, msg, _ = rodar(repo)
    assert cod == 1 and "api-legada/x.py" in msg


def test_mudanca_sem_commit_e_recusada(repo):
    commit(repo, {"api/tarefas.py": "x = 1\n"})
    (repo / "api" / "novo.py").write_text("y = 2\n")
    cod, msg, _ = rodar(repo)
    assert cod == 1 and "sem commit" in msg


def test_passo_errado_e_recusado(repo):
    commit(repo, {"api/tarefas.py": "x = 1\n"})
    cod, msg, _ = rodar(repo, passo="2")
    assert cod == 1 and "passo 1" in msg


def test_arquivo_de_teste_no_lugar_do_evento_explica_o_erro(repo):
    commit(repo, {"api/tarefas.py": "x = 1\n"})
    ev = repo / "build.json"
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--passo", "1", "--builder", "Backend",
                        "--testes-red", str(repo / "api/tests/test_t.py"), "--diretorios", "api/", "--resumo", "concluir grava",
                        "--evento", str(ev)], capture_output=True, text=True)
    assert r.returncode == 1 and "espera o arquivo do evento testes_red" in r.stderr


def entrada(repo, diretorios=("api/",)):
    red = json.loads((repo / "red.json").read_text())
    e = {"capacidade": "todo", "passo": 1, "spec": {"id": 1, "descricao": "concluir", "diretorios": list(diretorios)},
         "testes_red": red}
    (repo / "entrada.json").write_text(json.dumps(e))
    return repo / "entrada.json"


def rodar_entrada(repo, arq):
    ev = repo / "build.json"
    if ev.exists():
        ev.unlink()
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--passo", "1", "--builder", "Backend",
                        "--testes-red", str(arq), "--resumo", "concluir grava a tarefa", "--evento", str(ev)],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr, (json.loads(ev.read_text()) if ev.exists() else None)


def test_arquivo_de_entrada_traz_testes_red_e_diretorios(repo):
    commit(repo, {"api/tarefas.py": "def concluir(i):\n    return True\n"})
    cod, msg, ev = rodar_entrada(repo, entrada(repo))
    assert cod == 0, msg
    assert ev["arquivos"] == ["api/tarefas.py"]


def test_diretorios_da_entrada_valem_na_conferencia(repo):
    commit(repo, {"api/tarefas.py": "x = 1\n"})
    cod, msg, _ = rodar_entrada(repo, entrada(repo, diretorios=("web/",)))
    assert cod == 1 and "api/tarefas.py" in msg


def test_evento_testes_red_sem_diretorios_e_recusado(repo):
    commit(repo, {"api/tarefas.py": "x = 1\n"})
    cod, msg, _ = rodar_entrada(repo, repo / "red.json")
    assert cod == 1 and "sem diretórios" in msg


def test_commit_sem_linha_papel_e_recusado(repo):
    commit(repo, {"api/tarefas.py": "x = 1\n"}, papel=None)
    cod, msg, _ = rodar(repo)
    assert cod == 1 and "Papel:" in msg


def test_so_os_arquivos_dos_commits_do_builder_entram(repo):
    commit(repo, {"api/tarefas.py": "def concluir(i):\n    return True\n"})
    commit(repo, {"api/prompts/resumo.py": "P = 'x'\n"}, papel="AI")
    cod, msg, ev = rodar(repo)
    assert cod == 0, msg
    assert ev["arquivos"] == ["api/tarefas.py"]


def test_builder_sem_commit_proprio_e_recusado(repo):
    commit(repo, {"api/prompts/resumo.py": "P = 'x'\n"}, papel="AI")
    cod, msg, _ = rodar(repo)
    assert cod == 1 and "nenhum commit com 'Papel: Backend'" in msg


def test_commit_do_builder_desfeito_depois_nao_conta(repo):
    commit(repo, {"api/rascunho.py": "x = 1\n"})
    git(repo, "rm", "-q", "api/rascunho.py")
    git(repo, "commit", "-qm", "tira", "-m", "Papel: Backend")
    commit(repo, {"api/tarefas.py": "x = 2\n"})
    cod, msg, ev = rodar(repo)
    assert cod == 0, msg
    assert ev["arquivos"] == ["api/tarefas.py"]
