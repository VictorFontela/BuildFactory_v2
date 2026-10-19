"""Confere um evento antes de entregá-lo.

Uso:
    python .agents/shared/validar.py <tipo> <arquivo.json>

Saída 0: evento válido. Saída 1: evento inválido (cada erro numa linha, com o
campo). Saída 2: uso errado, arquivo ausente ou JSON ilegível.
Os exemplos de cada tipo estão em .agents/shared/exemplos/.
"""
import json
import sys
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eventos import TIPOS, validar  # noqa: E402


def principal(args: list[str]) -> int:
    if len(args) != 2:
        print(f"uso: validar.py <tipo> <arquivo.json>\ntipos: {', '.join(TIPOS)}")
        return 2
    tipo, arquivo = args
    if tipo not in TIPOS:
        print(f"tipo desconhecido: {tipo!r}\ntipos: {', '.join(TIPOS)}")
        return 2
    caminho = Path(arquivo)
    if not caminho.is_file():
        print(f"arquivo não encontrado: {arquivo}")
        return 2
    texto = caminho.read_text(encoding="utf-8")
    if texto.lstrip().startswith("```"):
        print("o arquivo começa com ```: grave só o JSON, sem a cerca de markdown")
        return 2
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as e:
        print(f"JSON ilegível na linha {e.lineno}, coluna {e.colno}: {e.msg}")
        return 2
    if not isinstance(dados, dict):
        print("o evento precisa ser um objeto JSON")
        return 2
    try:
        validar(dados, tipo)
    except ValidationError as e:
        print(f"{tipo}: {e.error_count()} erro(s)")
        for err in e.errors():
            campo = ".".join(str(p) for p in err["loc"]) or "(evento)"
            print(f"- {campo}: {err['msg']}")
        return 1
    except ValueError as e:
        print(f"{tipo}: {e}")
        return 1
    print(f"ok {tipo}")
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
