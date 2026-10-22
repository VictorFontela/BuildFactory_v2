"""apagar_sobras.py: apaga só o que listar_sobras põe em remover, e grava o evento."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_listar_sobras import git, repo  # noqa: E402,F401

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "apagar_sobras.py"
VALIDAR = Path(__file__).resolve().parents[3] / "shared" / "validar.py"


def apagar(r):
    evento = r / ".agents" / "state" / "cap" / "saidas" / "limpeza.json"
    p = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(r), "--capacidade", "cap", "--evento", str(evento)],
                       capture_output=True, text=True)
    return p.returncode, p.stderr, (json.loads(evento.read_text()) if evento.is_file() else None), evento


def test_apaga_o_novo_e_o_rascunho_e_mantem_o_resto(repo):
    (repo / "app/.tmp-mock.json").write_text("{}")
    (repo / "saida-build").mkdir()
    (repo / "saida-build/a.txt").write_text("x")
    rascunho = repo / ".agents/state/cap/rascunho"
    rascunho.mkdir(parents=True)
    (rascunho / "print.png").write_bytes(b"png")
    cod, err, ev, arquivo = apagar(repo)
    assert cod == 0, err
    assert sorted(ev["removidos"]) == sorted(["app/.tmp-mock.json", "saida-build/", ".agents/state/cap/rascunho/"])
    assert not (repo / "app/.tmp-mock.json").exists() and not (repo / "saida-build").exists() and not rascunho.exists()
    assert (repo / ".env").is_file() and (repo / "notas-do-humano.txt").is_file()
    assert (repo / ".agents/state/cap/baseline-suite.json").is_file()
    assert any(m.startswith(".env — ") for m in ev["mantidos"])
    v = subprocess.run([sys.executable, "-I", str(VALIDAR), "limpeza_feita", str(arquivo)], capture_output=True, text=True)
    assert v.returncode == 0, v.stdout + v.stderr


def test_nada_para_apagar_grava_evento_vazio(repo):
    cod, err, ev, _ = apagar(repo)
    assert cod == 0, err
    assert ev["removidos"] == []


def test_link_apagado_e_so_o_link(repo, tmp_path_factory):
    fora = tmp_path_factory.mktemp("fora") / "importante.txt"
    fora.write_text("do humano")
    (repo / "atalho").symlink_to(fora)
    cod, err, ev, _ = apagar(repo)
    assert cod == 0, err
    assert ev["removidos"] == ["atalho"] and not (repo / "atalho").is_symlink()
    assert fora.read_text() == "do humano"


def test_sem_linha_de_base_nao_apaga_nada(repo):
    (repo / "app/.tmp-mock.json").write_text("{}")
    (repo / ".agents/state/cap/baseline-suite.json").unlink()
    cod, err, ev, _ = apagar(repo)
    assert cod == 2 and "linha de base" in err and ev is None
    assert (repo / "app/.tmp-mock.json").is_file()


def test_uso_errado(repo):
    p = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(repo), "--capacidade", "cap"], capture_output=True, text=True)
    assert p.returncode == 2 and "Uso" in p.stderr
