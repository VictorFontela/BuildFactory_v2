"""Confere o green de um passo: testes do passo passando, testes intocados, diretórios e suíte inteira sem falha nova.

Uso (a partir da raiz do repositório):
    # no começo da capacidade, antes de qualquer mudança (o Orchestrator, uma vez):
    python .agents/skills/reviewer/scripts/rodar_green.py --gravar-baseline --capacidade <nome>

    # na revisão de cada passo (o Reviewer):
    python .agents/skills/reviewer/scripts/rodar_green.py --testes-red <arquivo de entrada> --saida <relatório.json>

O comando da suíte e o caminho do JUnit vêm de `.agents/projeto.json`
({"suite": "...", "junit": "..." ou ["...", "..."] quando a suíte grava mais de
um relatório}); --suite e --junit os substituem. Com o
arquivo de entrada do papel, os diretórios vêm da spec do passo e a linha de
base de `.agents/state/<capacidade>/baseline-suite.json`; com o arquivo do
evento testes_red, passe --diretorios e --baseline.

A suíte roda uma vez. Dela saem os testes do passo (os arquivos do testes_red) e
as falhas novas: falha que não estava na linha de base. Sem linha de base,
qualquer falha da suíte conta como nova.

Saída 0: green aceito. 1: reprovado, o relatório diz por quê. 2: uso errado ou
a suíte não rodou.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SHARED = Path(__file__).resolve().parents[3] / "shared"
sys.path.insert(0, str(SHARED))
from contexto import ContextoInvalido, ler_projeto, ler_testes_red  # noqa: E402
from junit import RelatorioInvalido, caso_do_arquivo, id_do_caso, ler_varios  # noqa: E402


class Uso(Exception):
    pass


def _git(raiz, *args):
    r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise Uso(f"git {' '.join(args)} falhou: {r.stderr.strip()}")
    return r.stdout


def dentro(arquivo, diretorios):
    return any(arquivo == d.rstrip("/") or arquivo.startswith(d.rstrip("/") + "/") for d in diretorios)


def rodar_suite(raiz, suite, junit):
    rels = [raiz / j for j in ([junit] if isinstance(junit, str) else junit)]
    for rel in rels:
        if rel.exists():
            rel.unlink()
    # bytecode num diretório novo: um .pyc velho com mesmo tamanho e mesmo segundo faria a suíte rodar código antigo
    with tempfile.TemporaryDirectory() as cache:
        subprocess.run(suite, shell=True, cwd=raiz, capture_output=True, text=True,
                       env={**os.environ, "PYTHONPYCACHEPREFIX": cache})
    try:
        return ler_varios(rels)
    except RelatorioInvalido as e:
        raise Uso(f"a suíte não rodou: {e}")


def caminho_baseline(raiz, capacidade):
    return Path(raiz) / ".agents" / "state" / capacidade / "baseline-suite.json"


def gravar_baseline(raiz, suite, junit, baseline):
    fora_antes = _git(raiz, "ls-files", "--others", "--directory", "--no-empty-directory", "--exclude=/.agents/state/")
    casos = rodar_suite(raiz, suite, junit)
    falhando = sorted(id_do_caso(c) for c in casos if c["tipo"] in ("falha", "erro"))
    fora = [l for l in fora_antes.splitlines() if l and not l.startswith(".agents/state/")]
    dados = {"commit": _git(raiz, "rev-parse", "--short=12", "HEAD").strip(), "total": len(casos), "falhando": falhando,
             "fora_do_git": fora}
    Path(baseline).parent.mkdir(parents=True, exist_ok=True)
    Path(baseline).write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dados


def conferir(raiz, testes_red, diretorios, suite, junit, baseline):
    raiz = Path(raiz).resolve()
    try:
        red, dirs_spec, capacidade = ler_testes_red(testes_red)
    except ContextoInvalido as e:
        raise Uso(str(e))
    diretorios = diretorios or dirs_spec
    if not diretorios:
        raise Uso("sem diretórios: passe --diretorios ou o arquivo de entrada do papel em --testes-red")
    if not baseline and capacidade:
        baseline = caminho_baseline(raiz, capacidade)
    mudados = [l for l in _git(raiz, "diff", "--name-only", f"{red.commit}..HEAD").splitlines() if l]
    testes_mexidos = sorted(set(mudados) & set(red.arquivos))
    fora = sorted(a for a in mudados if not dentro(a, diretorios))
    sujos = [l for l in _git(raiz, "status", "--porcelain", "--untracked-files=all", "--", *diretorios, *red.arquivos).splitlines() if l]

    casos = rodar_suite(raiz, suite, junit)
    do_passo = [c for c in casos if any(caso_do_arquivo(c, a) for a in red.arquivos)]
    passo_falhas = [f"{c['nome']}: {c['msg']}"[:300] for c in do_passo if c["tipo"] in ("falha", "erro")]
    sem_caso = [a for a in red.arquivos if not any(caso_do_arquivo(c, a) for c in casos)]

    base = json.loads(Path(baseline).read_text(encoding="utf-8")) if baseline and Path(baseline).is_file() else None
    ja = set(base["falhando"]) if base else set()
    novas = sorted(id_do_caso(c) for c in casos if c["tipo"] in ("falha", "erro") and id_do_caso(c) not in ja)

    rel = {
        "passo": red.passo,
        "testes_do_passo": {"total": len(do_passo), "falhas": passo_falhas, "arquivos_sem_caso": sem_caso},
        "testes_intocados": not testes_mexidos, "testes_mexidos": testes_mexidos,
        "fora_dos_diretorios": fora, "mudancas_sem_commit": sujos,
        "suite": {"total": len(casos), "novas_falhas": novas, "falhas_da_linha_de_base": len(ja),
                  "linha_de_base": base["commit"] if base else None},
    }
    motivos = []
    if passo_falhas or sem_caso or not do_passo:
        motivos.append(f"testes do passo não passam: {passo_falhas[:3] or sem_caso or 'nenhum caso encontrado'}")
    if testes_mexidos:
        motivos.append(f"testes alterados depois do red: {testes_mexidos}")
    if fora:
        motivos.append(f"arquivos fora dos diretórios do passo: {fora}")
    if sujos:
        motivos.append(f"mudanças sem commit: {sujos}")
    if novas:
        motivos.append(f"{len(novas)} falha(s) nova(s) na suíte: {novas[:5]}")
    if not base:
        rel["aviso"] = "sem linha de base: qualquer falha da suíte contou como nova"
    rel["ok"] = not motivos
    rel["motivos"] = motivos
    return rel


def principal(argv):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--gravar-baseline", action="store_true")
    p.add_argument("--testes-red")
    p.add_argument("--diretorios", nargs="+")
    p.add_argument("--capacidade")
    p.add_argument("--suite")
    p.add_argument("--junit", nargs="+")
    p.add_argument("--baseline")
    p.add_argument("--saida")
    p.add_argument("--raiz", default=".")
    try:
        a = p.parse_args(argv)
        if a.gravar_baseline:
            if not (a.baseline or a.capacidade):
                raise SystemExit
        elif not a.testes_red:
            raise SystemExit
    except SystemExit:
        print(__doc__, file=sys.stderr)
        return 2
    raiz = Path(a.raiz).resolve()
    try:
        projeto = ler_projeto(raiz)
        a.suite, a.junit = a.suite or projeto.get("suite"), a.junit or projeto.get("junit")
        if not (a.suite and a.junit):
            raise Uso("sem o comando da suíte: preencha .agents/projeto.json (suite e junit) ou passe --suite e --junit")
        if a.gravar_baseline:
            a.baseline = a.baseline or caminho_baseline(raiz, a.capacidade)
            d = gravar_baseline(raiz, a.suite, a.junit, a.baseline)
            print(f"linha de base gravada: {d['total']} testes, {len(d['falhando'])} já falhando, commit {d['commit']}")
            return 0
        rel = conferir(raiz, a.testes_red, a.diretorios, a.suite, a.junit, a.baseline)
    except (Uso, ContextoInvalido) as e:
        print(str(e), file=sys.stderr)
        return 2
    texto = json.dumps(rel, ensure_ascii=False, indent=2)
    if a.saida:
        Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
        Path(a.saida).write_text(texto + "\n", encoding="utf-8")
    print(texto)
    return 0 if rel["ok"] else 1


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
