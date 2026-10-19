"""resumo_mudancas.py: junta commits, arquivos, passos e o que pede atenção, sem mudar nada."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resumo_mudancas.py"


def git(r, *a):
    return subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True, text=True).stdout.strip()


def commit(r, arquivos, msg, papel=None):
    for n, t in arquivos.items():
        (r / n).parent.mkdir(parents=True, exist_ok=True)
        (r / n).write_text(t)
    git(r, "add", *arquivos)
    git(r, "commit", "-qm", msg, *(["-m", f"Papel: {papel}"] if papel else []))


def ev(r, n, d):
    p = r / ".agents/state/cap/eventos" / f"{n:04d}-{d['tipo']}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d))


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q"); git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    (tmp_path / ".gitignore").write_text(".agents/state/\n")
    commit(tmp_path, {".gitignore": ".agents/state/\n", "api/a.py": "x = 1\n"}, "base")
    base = git(tmp_path, "rev-parse", "--short=12", "HEAD")
    (tmp_path / ".agents/state/cap").mkdir(parents=True)
    (tmp_path / ".agents/state/cap/baseline-suite.json").write_text(json.dumps({"commit": base, "total": 1, "falhando": []}))
    ev(tmp_path, 1, {"tipo": "capacidade_criada", "capacidade": "cap", "pedido": "concluir tarefas"})
    ev(tmp_path, 3, {"tipo": "spec_pronta", "passos": [{"id": 1, "descricao": "API de concluir", "criterios": ["c"], "diretorios": ["api/"], "campos": {}}]})
    commit(tmp_path, {"api/tests/test_a.py": "def test(): pass\n"}, "test: red")
    commit(tmp_path, {"api/a.py": "x = 2\n", "requirements.txt": "fastapi\n", "migrations/001.sql": "create\n"}, "concluir", "Backend")
    ev(tmp_path, 7, {"tipo": "reprovacao", "passo": 1, "reprovou": "QA", "motivo": "falta 404", "arquivos": ["api/a.py"], "destino": ["Backend"], "porque": "x"})
    ev(tmp_path, 9, {"tipo": "aprovado", "passo": 1, "papel": "Reviewer", "evidencia": "ok"})
    ev(tmp_path, 10, {"tipo": "aprovado", "passo": 1, "papel": "QA", "evidencia": "ok"})
    return tmp_path, base


def rodar(r):
    p = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(r), "--capacidade", "cap"], capture_output=True, text=True)
    return p.returncode, (json.loads(p.stdout) if p.returncode == 0 else p.stderr)


def test_junta_commits_arquivos_passos_e_atencao(repo):
    r, base = repo
    cod, s = rodar(r)
    assert cod == 0, s
    assert s["base"] == base and s["head"] == git(r, "rev-parse", "--short=12", "HEAD")
    assert [c["papel"] for c in s["commits"]] == ["Tests", "Backend"]
    assert {a["arquivo"] for a in s["arquivos"]} == {"api/a.py", "api/tests/test_a.py", "requirements.txt", "migrations/001.sql"}
    assert s["atencao"] == {"dependencia": ["requirements.txt"], "migracao": ["migrations/001.sql"]}
    assert s["passos"] == [{"passo": 1, "descricao": "API de concluir", "aprovado_por": ["Reviewer", "QA"],
                            "voltas": [{"reprovou": "QA", "motivo": "falta 404"}]}]
    assert s["voltar_atras"]["sem_push"] == f"git reset --hard {base}" and s["remoto"] is False
    assert s["pedido"] == "concluir tarefas" and s["mudancas_sem_commit"] == []


def test_nao_muda_o_repositorio(repo):
    r, _ = repo
    antes = (git(r, "rev-parse", "HEAD"), git(r, "status", "--porcelain"))
    rodar(r)
    assert (git(r, "rev-parse", "HEAD"), git(r, "status", "--porcelain")) == antes


def test_mudanca_sem_commit_aparece(repo):
    r, _ = repo
    (r / "api/rascunho.py").write_text("y\n")
    _, s = rodar(r)
    assert s["mudancas_sem_commit"] == ["?? api/rascunho.py"]


def test_sem_linha_de_base_e_uso_errado(repo):
    r, _ = repo
    (r / ".agents/state/cap/baseline-suite.json").unlink()
    cod, msg = rodar(r)
    assert cod == 2 and "linha de base" in msg


def test_configuracao_e_infra(repo):
    r, _ = repo
    commit(r, {".env.example": "A=1\n", "Dockerfile": "FROM x\n", "app/settings.py": "X=1\n"}, "conf", "Backend")
    _, s = rodar(r)
    assert set(s["atencao"]["configuracao"]) == {".env.example", "app/settings.py"} and s["atencao"]["infra"] == ["Dockerfile"]


def test_voltas_e_aprovacoes_ficam_no_passo_certo(repo):
    r, _ = repo
    ev(r, 11, {"tipo": "spec_pronta", "passos": [
        {"id": 1, "descricao": "API de concluir", "criterios": ["c"], "diretorios": ["api/"], "campos": {}},
        {"id": 2, "descricao": "Tela", "criterios": ["c"], "diretorios": ["web/"], "campos": {}}]})
    ev(r, 12, {"tipo": "reprovacao", "passo": 2, "reprovou": "Reviewer", "motivo": "print", "arquivos": ["web/a.js"], "destino": ["Frontend"], "porque": "x"})
    ev(r, 13, {"tipo": "aprovado", "passo": 2, "papel": "Reviewer", "evidencia": "ok"})
    _, s = rodar(r)
    p1, p2 = s["passos"]
    assert p1["aprovado_por"] == ["Reviewer", "QA"] and [v["reprovou"] for v in p1["voltas"]] == ["QA"]
    assert p2["aprovado_por"] == ["Reviewer"] and [v["reprovou"] for v in p2["voltas"]] == ["Reviewer"]


def test_remoto_configurado_aparece(repo):
    r, _ = repo
    git(r, "remote", "add", "origin", "https://exemplo.invalid/x.git")
    _, s = rodar(r)
    assert s["remoto"] is True
