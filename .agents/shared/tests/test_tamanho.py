"""Instruções dos agentes: tamanho com teto e sem histórico do projeto.

Subir um teto é uma decisão: mude o número aqui, no mesmo commit que fez o texto crescer.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
AGENTS = RAIZ / ".agents"
SKILLS = sorted((AGENTS / "skills").glob("*/SKILL.md"))
REFERENCIAS = sorted((AGENTS / "skills").glob("*/references/*.md")) + sorted((AGENTS / "shared" / "guias").glob("*.md"))
INSTRUCOES = [RAIZ / "AGENTS.md", *SKILLS, *REFERENCIAS]

TETO_SKILL = 60
TETO_SKILL_ORCHESTRATOR = 120
TETO_REFERENCIA = 50
TETO_AGENTS = 15
TETO_PALAVRAS = 11000

# Medição, etapa e status pertencem às evidências; na instrução, envelhecem e o agente lê como regra.
HISTORICO = re.compile(r"\b[Nn]a (Etapa \d+|\d[a-z]\b|E\d+[a-z]?\b)|\bpronto \(E\d+|^## Pendências", re.MULTILINE)


def linhas(p):
    return len(p.read_text(encoding="utf-8").splitlines())


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_skill_dentro_do_teto(skill):
    teto = TETO_SKILL_ORCHESTRATOR if skill.parent.name == "orchestrator" else TETO_SKILL
    assert linhas(skill) <= teto, f"{skill.relative_to(RAIZ)}: {linhas(skill)} linhas, teto {teto}"


@pytest.mark.parametrize("ref", REFERENCIAS, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_referencia_dentro_do_teto(ref):
    assert linhas(ref) <= TETO_REFERENCIA, f"{ref.relative_to(RAIZ)}: {linhas(ref)} linhas, teto {TETO_REFERENCIA}"


def test_agents_md_dentro_do_teto():
    assert linhas(RAIZ / "AGENTS.md") <= TETO_AGENTS


def test_total_de_palavras_dentro_do_teto():
    total = sum(len(p.read_text(encoding="utf-8").split()) for p in INSTRUCOES)
    assert total <= TETO_PALAVRAS, f"{total} palavras nas instruções, teto {TETO_PALAVRAS}"


@pytest.mark.parametrize("arq", INSTRUCOES, ids=lambda p: str(p.relative_to(RAIZ)))
def test_sem_historico_do_projeto(arq):
    achados = [m.group(0) for m in HISTORICO.finditer(arq.read_text(encoding="utf-8"))]
    assert not achados, f"{arq.relative_to(RAIZ)}: {achados}"
