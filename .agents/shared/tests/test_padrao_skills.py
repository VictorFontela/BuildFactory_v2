"""As skills dos papéis seguem o mesmo esqueleto, na mesma ordem.

**Missão.** e depois: Entrada, Passos, Regras, Saída, Dúvida ou falta de informação, Nunca decide.
O Orchestrator fica de fora: ele roteia, não faz o trabalho de um passo.
Seção a mais é uma decisão: entra em EXTRAS, com o lugar dela, no mesmo commit.
"""
from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parents[2] / "skills"
PAPEIS = sorted(p for p in SKILLS.glob("*/SKILL.md") if p.parent.name != "orchestrator")
ORDEM = ["Entrada", "Passos", "Regras", "Saída", "Dúvida ou falta de informação", "Nunca decide"]
# DevOps traz o molde da página que o humano lê para decidir.
EXTRAS = {"devops": {"Modelo do pacote": "Passos"}}


def secoes(texto):
    """Os títulos ## fora de bloco de código, na ordem em que aparecem."""
    fora, achados = True, []
    for linha in texto.splitlines():
        if linha.startswith("```"):
            fora = not fora
        elif fora and linha.startswith("## "):
            achados.append(linha[3:].strip())
    return achados


def esperado(papel):
    ordem = list(ORDEM)
    for secao, depois in EXTRAS.get(papel, {}).items():
        ordem.insert(ordem.index(depois) + 1, secao)
    return ordem


def test_secoes_ignora_titulo_dentro_de_bloco():
    assert secoes("## A\n```markdown\n## B\n```\n## C") == ["A", "C"]


@pytest.mark.parametrize("skill", PAPEIS, ids=lambda p: p.parent.name)
def test_secoes_na_ordem(skill):
    assert secoes(skill.read_text(encoding="utf-8")) == esperado(skill.parent.name)


@pytest.mark.parametrize("skill", PAPEIS, ids=lambda p: p.parent.name)
def test_missao_antes_da_primeira_secao(skill):
    texto = skill.read_text(encoding="utf-8")
    assert "\n**Missão.** " in texto.split("\n## ", 1)[0]
