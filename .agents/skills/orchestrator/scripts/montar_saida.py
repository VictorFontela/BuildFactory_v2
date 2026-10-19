"""Monta e valida a ativação de um passo a partir dos campos que a Specification preencheu.

Uso:
    python montar_saida.py --campos campos.json

campos.json tem os 4 campos de um passo:
    {"interface": {"valor": true|false|"incerto", "trecho": "...", "decisao": true|false|null}, "servidor": ..., "agente_llm": ..., "seguranca": ...}

Builders ativos rodam em paralelo (todos dependem só de Tests).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import saida_ativacao  # noqa: E402

REGRA = {"interface": "Frontend", "servidor": "Backend", "agente_llm": "AI", "seguranca": "Security"}
BUILDERS = ["Frontend", "Backend", "AI"]


class CampoInvalido(ValueError):
    pass


def decidir(campos: dict) -> dict:
    """Devolve {ator: trecho} para os atores que atuam."""
    ativos = {}
    for campo, ator in REGRA.items():
        c = campos[campo]
        v = c["valor"]
        if v == "incerto":
            v = c.get("decisao")
            if v not in (True, False):
                raise CampoInvalido(f"{campo}: incerto sem decisão true/false")
        if v is True:
            ativos[ator] = c.get("trecho", "")
        elif v is not False:
            raise CampoInvalido(f"{campo}: valor {v!r} inválido")
    return ativos


def montar(campos: dict) -> dict:
    ativos = decidir(campos)
    bs = [b for b in BUILDERS if b in ativos]
    saida = {
        "builders": {b: {"ativo": b in ativos, "trecho": ativos.get(b, "")} for b in BUILDERS},
        "security": {"ativo": "Security" in ativos, "trecho": ativos.get("Security", "")},
        "builders_em_paralelo": len(bs) >= 2,
    }
    return saida_ativacao.Saida.model_validate(saida).model_dump()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--campos", required=True)
    a = p.parse_args()
    print(json.dumps(montar(json.loads(Path(a.campos).read_text())), ensure_ascii=False, indent=2))
