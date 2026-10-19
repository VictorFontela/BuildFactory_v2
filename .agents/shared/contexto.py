"""Lê o que os scripts dos papéis precisam: o testes_red do passo, os diretórios e a configuração da suíte.

`--testes-red` aceita o arquivo do evento testes_red ou o arquivo de entrada que
o Orchestrator passa ao papel (ele traz o testes_red e a spec do passo).
"""
import json
from pathlib import Path

from eventos import validar


class ContextoInvalido(Exception):
    pass


def ler_testes_red(caminho):
    """Devolve (testes_red, diretorios do passo ou None, capacidade ou None)."""
    try:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except Exception:
        dados = None
    if isinstance(dados, dict) and isinstance(dados.get("testes_red"), dict):
        spec = dados.get("spec") or {}
        try:
            return validar(dados["testes_red"], "testes_red"), spec.get("diretorios"), dados.get("capacidade")
        except Exception:
            pass
    elif isinstance(dados, dict) and dados.get("tipo") == "testes_red":
        try:
            return validar(dados, "testes_red"), None, None
        except Exception:
            pass
    raise ContextoInvalido(f"--testes-red espera o arquivo do evento testes_red ou o arquivo de entrada do papel "
                           f"(JSON gravado pelos scripts), não o arquivo de teste: {caminho}")


def ler_projeto(raiz):
    """`.agents/projeto.json`: {"suite": comando da suíte inteira gravando JUnit, "junit": caminho do XML}."""
    p = Path(raiz) / ".agents" / "projeto.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ContextoInvalido(f".agents/projeto.json ilegível: {e}")
