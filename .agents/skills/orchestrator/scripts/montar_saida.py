"""Monta e valida a saída do Orchestrator a partir dos campos que a Specification preencheu.

Uso:
    python montar_saida.py --campos campos.json [--selecao hibrida|regras] [--formato ativacao|dag]

campos.json tem os 4 campos de um passo:
    {"interface": {"valor": true|false|"incerto", "trecho": "...", "decisao": true|false|null}, "servidor": ..., "agente_llm": ..., "seguranca": ...}

Builders ativos rodam em paralelo (todos dependem só de Tests). Ver pendência na SKILL.md.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import saida_ativacao  # noqa: E402
import saida_dag  # noqa: E402

REGRA = {"interface": "Frontend", "servidor": "Backend", "agente_llm": "AI", "seguranca": "Security"}
BUILDERS = ["Frontend", "Backend", "AI"]


class CampoInvalido(ValueError):
    pass


def decidir(campos: dict, selecao: str) -> dict:
    """Devolve {ator: trecho} para os atores que atuam."""
    ativos = {}
    for campo, ator in REGRA.items():
        c = campos[campo]
        v = c["valor"]
        if v == "incerto":
            if selecao != "hibrida":
                raise CampoInvalido(f"{campo}: 'incerto' só vale na seleção híbrida")
            v = c.get("decisao")
            if v not in (True, False):
                raise CampoInvalido(f"{campo}: incerto sem decisão true/false")
        if v is True:
            ativos[ator] = c.get("trecho", "")
        elif v is not False:
            raise CampoInvalido(f"{campo}: valor {v!r} inválido")
    return ativos


def ativacao(ativos: dict) -> dict:
    bs = [b for b in BUILDERS if b in ativos]
    saida = {
        "builders": {b: {"ativo": b in ativos, "trecho": ativos.get(b, "")} for b in BUILDERS},
        "security": {"ativo": "Security" in ativos, "trecho": ativos.get("Security", "")},
        "builders_em_paralelo": len(bs) >= 2,
    }
    return saida_ativacao.Saida.model_validate(saida).model_dump()


def dag(ativos: dict) -> dict:
    bs = [b for b in BUILDERS if b in ativos]
    sec = "Security" in ativos
    nos = [{"ator": "Specification", "depende_de": []}, {"ator": "Tests", "depende_de": ["Specification"]}]
    nos += [{"ator": b, "depende_de": ["Tests"]} for b in bs]
    nos += [{"ator": "Reviewer", "depende_de": bs or ["Tests"]}, {"ator": "QA", "depende_de": ["Reviewer"]}]
    if sec:
        nos.append({"ator": "Security", "depende_de": ["QA"]})
    nos += [{"ator": "DevOps", "depende_de": ["Security" if sec else "QA"]}, {"ator": "Cleanup", "depende_de": ["DevOps"]}]
    return saida_dag.Saida.model_validate({"nos": nos}).model_dump()


def montar(campos: dict, selecao: str = "hibrida", formato: str = "ativacao") -> dict:
    ativos = decidir(campos, selecao)
    return ativacao(ativos) if formato == "ativacao" else dag(ativos)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--campos", required=True)
    p.add_argument("--selecao", choices=["hibrida", "regras"], default="hibrida")
    p.add_argument("--formato", choices=["ativacao", "dag"], default="ativacao")
    a = p.parse_args()
    print(json.dumps(montar(json.loads(Path(a.campos).read_text()), a.selecao, a.formato), ensure_ascii=False, indent=2))
