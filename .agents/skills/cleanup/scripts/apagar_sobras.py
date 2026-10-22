"""Apaga as sobras da capacidade e grava o evento limpeza_feita.

Uso (a partir da raiz do repositório):
    python .agents/skills/cleanup/scripts/apagar_sobras.py --capacidade <nome> --evento <arquivo do evento>

Refaz a lista do listar_sobras.py (não confia numa lista gravada antes) e apaga
só o que está em `remover`, um caminho por vez, sempre dentro do repositório.
Depois confere que nada rastreado pelo git mudou e grava o evento: `removidos`
são os caminhos que ele apagou; `mantidos`, os de `manter` e de `avisar`, cada
um com o motivo depois de ` — `.

Saída 0: apagou e gravou o evento. 1: algo rastreado mudou durante a remoção;
o evento não é gravado. 2: uso errado, sem linha de base ou falha do git; nada
é apagado.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parents[2] / "shared"))
from eventos import validar  # noqa: E402
from listar_sobras import Uso, git, listar  # noqa: E402


class Recusa(Exception):
    pass


def alvo(raiz, capacidade, caminho):
    """O caminho dentro do repositório; fora dele, ou no registro da capacidade, é erro de uso.
    Não segue link: um link apagado é só o link."""
    p = Path(os.path.abspath(raiz / caminho))
    estado = raiz / ".agents" / "state"
    rascunho = estado / capacidade / "rascunho"
    if p == raiz or raiz not in p.parents or p == raiz / ".git" or raiz / ".git" in p.parents:
        raise Uso(f"{caminho}: fora do repositório")
    if (p == estado or estado in p.parents) and not (p == rascunho or rascunho in p.parents):
        raise Uso(f"{caminho}: é do registro da capacidade")
    return p


def apagar(raiz, capacidade):
    raiz = Path(raiz).resolve()
    lista = listar(raiz, capacidade)
    alvos = [(i["caminho"], alvo(raiz, capacidade, i["caminho"])) for i in lista["remover"]]
    rastreado = git(raiz, "status", "--porcelain", "--untracked-files=no")
    removidos = []
    for caminho, p in alvos:
        if p.is_symlink() or p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
        removidos.append(caminho)
    if git(raiz, "status", "--porcelain", "--untracked-files=no") != rastreado:
        raise Recusa(f"algo rastreado pelo git mudou depois de apagar {removidos}: confira com git status e mostre ao humano")
    mantidos = [f"{i['caminho']} — {i['por_que']}" for i in lista["manter"] + lista["avisar"]]
    return validar({"tipo": "limpeza_feita", "removidos": removidos, "mantidos": mantidos}).model_dump(mode="json")


def principal(argv):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--capacidade", required=True)
    p.add_argument("--evento", required=True)
    p.add_argument("--raiz", default=".")
    try:
        a = p.parse_args(argv)
    except SystemExit:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        ev = apagar(a.raiz, a.capacidade)
    except Uso as e:
        print(f"nada apagado: {e}", file=sys.stderr)
        return 2
    except Recusa as e:
        print(f"limpeza recusada: {e}", file=sys.stderr)
        return 1
    destino = Path(a.evento)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"limpeza feita: {len(ev['removidos'])} removido(s); evento em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
