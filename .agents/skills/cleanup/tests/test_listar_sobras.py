"""listar_sobras.py: só o que apareceu fora do git durante a capacidade vai para remover."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "listar_sobras.py"
GREEN = Path(__file__).resolve().parents[2] / "reviewer" / "scripts" / "rodar_green.py"


def git(r, *a):
    return subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q"); git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    (tmp_path / ".gitignore").write_text("__pycache__/\n.env\n.agents/state/\n")
    (tmp_path / "app").mkdir()
    (tmp_path / "app/a.py").write_text("x = 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_a.py").write_text("def test_a():\n    assert True\n")
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-qm", "base")
    (tmp_path / ".env").write_text("SEGREDO=1\n")
    (tmp_path / "notas-do-humano.txt").write_text("minhas notas\n")
    suite = f"{sys.executable} -m pytest -q -p no:cacheprovider --junitxml=.agents/state/s.xml"
    r = subprocess.run([sys.executable, "-I", str(GREEN), "--raiz", str(tmp_path), "--gravar-baseline", "--capacidade", "cap",
                        "--suite", suite, "--junit", ".agents/state/s.xml"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return tmp_path


def rodar(r):
    p = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(r), "--capacidade", "cap"], capture_output=True, text=True)
    return p.returncode, (json.loads(p.stdout) if p.returncode == 0 else p.stderr)


def test_o_que_ja_existia_fica_e_o_novo_sai(repo):
    (repo / "app/rascunho.py").write_text("y\n")
    (repo / "saida_debug.log").write_text("log\n")
    (repo / "tmpdir").mkdir()
    (repo / "tmpdir/x").write_text("x\n")
    (repo / "app/__pycache__").mkdir()
    (repo / "app/__pycache__/a.pyc").write_bytes(b"0")
    cod, s = rodar(repo)
    assert cod == 0, s
    assert sorted(x["caminho"] for x in s["remover"]) == ["app/rascunho.py", "saida_debug.log", "tmpdir/"]
    mantidos = {x["caminho"] for x in s["manter"]}
    assert {".env", "notas-do-humano.txt", "app/__pycache__/", ".agents/state/cap/"} <= mantidos


def test_rascunho_que_entrou_em_commit_vai_para_aviso(repo):
    (repo / "app/rascunho.py").write_text("y\n")
    git(repo, "add", "app/rascunho.py"); git(repo, "commit", "-qm", "x")
    _, s = rodar(repo)
    assert [x["caminho"] for x in s["avisar"]] == ["app/rascunho.py"] and s["remover"] == []


def test_nao_apaga_nada(repo):
    (repo / "novo.tmp").write_text("x\n")
    rodar(repo)
    assert (repo / "novo.tmp").exists()


def test_sem_linha_de_base_e_uso_errado(repo):
    (repo / ".agents/state/cap/baseline-suite.json").unlink()
    cod, msg = rodar(repo)
    assert cod == 2 and "linha de base" in msg


def test_arquivo_rastreado_so_modificado_nao_vira_aviso(repo):
    (repo / "app/debug_util.py").write_text("a\n")
    git(repo, "add", "-A"); git(repo, "commit", "-qm", "util")
    b = repo / ".agents/state/cap/baseline-suite.json"
    d = json.loads(b.read_text()); d["commit"] = git(repo, "rev-parse", "--short=12", "HEAD"); b.write_text(json.dumps(d))
    (repo / "app/debug_util.py").write_text("b\n")
    git(repo, "commit", "-qam", "muda")
    _, s = rodar(repo)
    assert s["avisar"] == []


def test_linha_de_base_antiga_sem_fora_do_git_e_uso_errado(repo):
    b = repo / ".agents/state/cap/baseline-suite.json"
    d = json.loads(b.read_text()); del d["fora_do_git"]; b.write_text(json.dumps(d))
    cod, msg = rodar(repo)
    assert cod == 2 and "versão antiga" in msg
