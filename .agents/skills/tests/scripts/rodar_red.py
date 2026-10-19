"""Confere que os testes de um passo estão red pelo motivo certo e grava o evento testes_red.

Uso (a partir da raiz do repositório):
    python .agents/skills/tests/scripts/rodar_red.py --passo 1 \
        --comando "pytest api/tests/test_x.py --junitxml=.agents/tmp/red.xml" \
        --junit .agents/tmp/red.xml --arquivos api/tests/test_x.py --evento <arquivo do evento>

O comando roda os testes e precisa gravar o relatório em JUnit XML no caminho
de --junit (pytest: --junitxml; jest: jest-junit; vitest: --reporter=junit;
node:test: --test-reporter=./.agents/shared/reporters/junit-node.mjs). Passo com
testes em duas linguagens: um comando que roda as duas e os dois caminhos em --junit.

Red aceito quando:
  - há pelo menos 1 falha e nenhum erro (erro = import, sintaxe ou coleta:
    o teste nem rodou);
  - todo arquivo em --arquivos tem pelo menos 1 caso no relatório;
  - o último commit tem só os arquivos em --arquivos, e eles não têm mudança
    fora do commit.
O script preenche `falhas` (do relatório) e `commit` (do git); o papel não
digita esses dois campos.

Saída 0: red aceito, evento gravado. 1: recusado, com o motivo. 2: uso errado.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[3] / "shared"
sys.path.insert(0, str(SHARED))
from eventos import validar  # noqa: E402
from junit import RelatorioInvalido, caso_do_arquivo, ler_varios  # noqa: E402


class Recusa(Exception):
    pass


def _git(raiz, *args):
    r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise Recusa(f"git {' '.join(args)} falhou: {r.stderr.strip()}")
    return r.stdout


def conferir(raiz, passo, comando, junit, arquivos):
    raiz = Path(raiz).resolve()
    rels = [raiz / j for j in ([junit] if isinstance(junit, str) else junit)]
    for rel in rels:
        if rel.exists():
            rel.unlink()
    r = subprocess.run(comando, shell=True, cwd=raiz, capture_output=True, text=True)
    try:
        casos = ler_varios(rels)
    except RelatorioInvalido as e:
        raise Recusa(str(e))
    erros = [c for c in casos if c["tipo"] == "erro"]
    if erros:
        e = erros[0]
        raise Recusa(f"{len(erros)} erro(s) antes de o teste rodar (import, sintaxe ou coleta); "
                     f"primeiro: {e['classe'] or e['nome']}: {e['msg']}")
    falhas = [c for c in casos if c["tipo"] == "falha"]
    if not casos:
        raise Recusa("nenhum teste encontrado no relatório")
    if not falhas:
        raise Recusa(f"nenhuma falha: os {len(casos)} testes já passam, então não estão red")
    if r.returncode == 0:
        raise Recusa("o relatório tem falhas, mas o comando saiu com 0: confira se o comando é o dos testes")
    sem_caso = [a for a in arquivos if not any(caso_do_arquivo(c, a) for c in casos)]
    if sem_caso:
        raise Recusa(f"arquivo de teste sem nenhum caso no relatório: {sem_caso}")
    no_commit = [l for l in _git(raiz, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines() if l]
    fora = sorted(set(no_commit) - set(arquivos))
    if fora:
        raise Recusa(f"o último commit tem arquivos que não são os testes do evento: {fora}")
    faltam = sorted(set(arquivos) - set(no_commit))
    if faltam:
        raise Recusa(f"testes do evento fora do último commit: {faltam}")
    sujos = [l for l in _git(raiz, "status", "--porcelain", "--", *arquivos).splitlines() if l]
    if sujos:
        raise Recusa(f"testes com mudança fora do commit: {sujos}")
    commit = _git(raiz, "rev-parse", "--short=12", "HEAD").strip()
    evento = {"tipo": "testes_red", "passo": passo, "arquivos": list(arquivos), "comando": comando,
              "falhas": [f"{c['nome']}: {c['msg']}"[:300] for c in falhas], "commit": commit}
    return validar(evento, "testes_red").model_dump(mode="json")


def principal(argv):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--passo", type=int, required=True)
    p.add_argument("--comando", required=True)
    p.add_argument("--junit", nargs="+", required=True)
    p.add_argument("--arquivos", nargs="+", required=True)
    p.add_argument("--evento", required=True)
    p.add_argument("--raiz", default=".")
    try:
        a = p.parse_args(argv)
    except SystemExit:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        ev = conferir(a.raiz, a.passo, a.comando, a.junit, a.arquivos)
    except Recusa as e:
        print(f"red recusado: {e}", file=sys.stderr)
        return 1
    destino = Path(a.evento)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"red aceito: {len(ev['falhas'])} falha(s), commit {ev['commit']}; evento em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
