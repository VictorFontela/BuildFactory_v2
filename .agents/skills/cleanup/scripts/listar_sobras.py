"""Lista o que sobrou da construção da capacidade e pode sair.

Uso (a partir da raiz do repositório):
    python .agents/skills/cleanup/scripts/listar_sobras.py --capacidade <nome> [--saida <arquivo.json>]

Compara o que está fora do git agora com o que estava no começo da capacidade
(`fora_do_git` na linha de base) e devolve:
  - remover: arquivos e pastas fora do git que apareceram durante a capacidade;
  - manter: o que já existia antes, os caches que se refazem sozinhos e
    `.agents/state/` (o registro da capacidade);
  - avisar: arquivos com cara de rascunho que entraram em commit na capacidade
    (o Cleanup não os apaga: passaram pela revisão; vão para o humano).
Não apaga nada.

Saída 0: ok. 2: capacidade sem linha de base.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CACHE = re.compile(r"(^|/)(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|node_modules|\.cache|\.venv|venv)(/|$)|\.pyc$")
RASCUNHO = re.compile(r"(^|/)(rascunho|scratch|tmp|temp|debug)[^/]*$|\.(tmp|bak|orig|swp)$|~$", re.I)


class Uso(Exception):
    pass


def git(raiz, *a):
    r = subprocess.run(["git", "-C", str(raiz), *a], capture_output=True, text=True)
    if r.returncode != 0:
        raise Uso(f"git {' '.join(a)} falhou: {r.stderr.strip()}")
    return r.stdout


def listar(raiz, capacidade):
    raiz = Path(raiz).resolve()
    b = raiz / ".agents" / "state" / capacidade / "baseline-suite.json"
    if not b.is_file():
        raise Uso(f"sem linha de base em {b.relative_to(raiz)}: sem ela não dá para saber o que a capacidade criou")
    base = json.loads(b.read_text(encoding="utf-8"))
    if "fora_do_git" not in base:
        raise Uso("a linha de base é de uma versão antiga e não guardou o que estava fora do git: liste à mão e pergunte ao humano")
    antes = set(base["fora_do_git"])
    agora = [l for l in git(raiz, "ls-files", "--others", "--directory", "--no-empty-directory", "--exclude=/.agents/state/").splitlines() if l]
    remover, manter = [], [{"caminho": f".agents/state/{capacidade}/", "por_que": "registro da capacidade"}]
    for c in agora:
        if c in antes:
            manter.append({"caminho": c, "por_que": "já existia antes da capacidade"})
        elif CACHE.search(c):
            manter.append({"caminho": c, "por_que": "cache que se refaz sozinho"})
        else:
            remover.append({"caminho": c, "por_que": "apareceu durante a capacidade e não está no git"})
    novos = [l[2:].strip() for l in git(raiz, "diff", "--name-status", f"{base['commit']}..HEAD").splitlines() if l.startswith("A")]
    avisar = [{"caminho": c, "por_que": "entrou em commit com nome de rascunho: o humano decide"} for c in novos if RASCUNHO.search(c)]
    return {"capacidade": capacidade, "remover": remover, "manter": manter, "avisar": avisar}


def principal(argv):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--capacidade", required=True)
    p.add_argument("--saida")
    p.add_argument("--raiz", default=".")
    try:
        a = p.parse_args(argv)
    except SystemExit:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        r = listar(a.raiz, a.capacidade)
    except Uso as e:
        print(str(e), file=sys.stderr)
        return 2
    texto = json.dumps(r, ensure_ascii=False, indent=2)
    if a.saida:
        Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
        Path(a.saida).write_text(texto + "\n", encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
