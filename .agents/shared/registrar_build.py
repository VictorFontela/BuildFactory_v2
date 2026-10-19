"""Grava o evento build_pronto de um builder, a partir do git.

Uso (a partir da raiz do repositório):
    python .agents/shared/registrar_build.py --passo 1 --builder Backend \
        --testes-red <arquivo de entrada do papel, ou do evento testes_red> \
        --resumo "o que mudou, em uma frase" --evento <arquivo do evento>

Com o arquivo de entrada, os diretórios vêm da spec do passo; --diretorios só
é preciso com o arquivo do evento testes_red.

Cada commit do builder termina com a linha `Papel: <builder>`:
    git commit -m "<o que mudou>" -m "Papel: Backend"
É por ela que o script separa os arquivos de cada builder quando mais de um
atua no mesmo passo.

Confere, desde o commit dos testes (o `commit` do testes_red):
  - todo commit novo tem a linha `Papel:`; pelo menos um é deste builder;
  - nenhum arquivo de teste do testes_red foi alterado;
  - todo arquivo dos commits deste builder está dentro dos diretórios do passo;
  - não há mudança sem commit nesses diretórios.
Preenche `arquivos` (os dos commits deste builder) e `commit` a partir do git;
o builder só escreve o resumo.

Saída 0: evento gravado. 1: recusado, com o motivo. 2: uso errado.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contexto import ContextoInvalido, ler_testes_red  # noqa: E402
from eventos import validar  # noqa: E402


PAPEL = re.compile(r"^Papel: *(Frontend|Backend|AI) *$", re.M)


class Recusa(Exception):
    pass


def _git(raiz, *args):
    r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise Recusa(f"git {' '.join(args)} falhou: {r.stderr.strip()}")
    return r.stdout


def dentro(arquivo, diretorios):
    return any(arquivo == d.rstrip("/") or arquivo.startswith(d.rstrip("/") + "/") for d in diretorios)


def conferir(raiz, passo, builder, testes_red, diretorios, resumo):
    raiz = Path(raiz).resolve()
    try:
        red, dirs_spec, _ = ler_testes_red(testes_red)
    except ContextoInvalido as e:
        raise Recusa(str(e))
    diretorios = diretorios or dirs_spec
    if not diretorios:
        raise Recusa("sem diretórios: passe --diretorios ou o arquivo de entrada do papel em --testes-red")
    if red.passo != passo:
        raise Recusa(f"o testes_red é do passo {red.passo}, não do {passo}")
    mudados = [l for l in _git(raiz, "diff", "--name-only", f"{red.commit}..HEAD").splitlines() if l]
    if not mudados:
        raise Recusa(f"nenhuma mudança com commit desde os testes ({red.commit})")
    testes = sorted(set(mudados) & set(red.arquivos))
    if testes:
        raise Recusa(f"arquivos de teste alterados: {testes}. Teste errado se resolve com duvida_contrato, não mexendo nele")
    meus, sem_papel = set(), []
    for c in _git(raiz, "rev-list", f"{red.commit}..HEAD").split():
        papeis = PAPEL.findall(_git(raiz, "log", "-1", "--format=%B", c))
        if not papeis:
            sem_papel.append(c[:12])
        elif builder in papeis:
            meus.update(l for l in _git(raiz, "diff-tree", "--no-commit-id", "--name-only", "-r", c).splitlines() if l)
    if sem_papel:
        raise Recusa(f"commit sem a linha 'Papel: <builder>': {sem_papel}. Refaça a mensagem com "
                     f"git commit --amend -m \"<o que mudou>\" -m \"Papel: {builder}\" (ou rebase, se for mais de um)")
    if not meus:
        raise Recusa(f"nenhum commit com 'Papel: {builder}' desde os testes ({red.commit})")
    mudados = sorted(m for m in meus if m in set(mudados))
    if not mudados:
        raise Recusa(f"os commits de {builder} não deixaram mudança desde os testes ({red.commit})")
    fora = sorted(a for a in mudados if not dentro(a, diretorios))
    if fora:
        raise Recusa(f"arquivos fora dos diretórios do passo {diretorios}: {fora}")
    sujos = [l for l in _git(raiz, "status", "--porcelain", "--untracked-files=all", "--", *diretorios).splitlines() if l]
    if sujos:
        raise Recusa(f"mudanças sem commit nos diretórios do passo: {sujos}")
    commit = _git(raiz, "rev-parse", "--short=12", "HEAD").strip()
    ev = {"tipo": "build_pronto", "passo": passo, "builder": builder, "arquivos": mudados, "resumo": resumo, "commit": commit}
    return validar(ev, "build_pronto").model_dump(mode="json")


def principal(argv):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--passo", type=int, required=True)
    p.add_argument("--builder", required=True)
    p.add_argument("--testes-red", required=True)
    p.add_argument("--diretorios", nargs="+")
    p.add_argument("--resumo", required=True)
    p.add_argument("--evento", required=True)
    p.add_argument("--raiz", default=".")
    try:
        a = p.parse_args(argv)
    except SystemExit:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        ev = conferir(a.raiz, a.passo, a.builder, a.testes_red, a.diretorios, a.resumo)
    except Recusa as e:
        print(f"build recusado: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"build recusado: {e}", file=sys.stderr)
        return 1
    destino = Path(a.evento)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"build aceito: {len(ev['arquivos'])} arquivo(s), commit {ev['commit']}; evento em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
