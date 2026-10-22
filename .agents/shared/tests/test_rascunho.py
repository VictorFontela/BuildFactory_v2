"""O rascunho dos papéis fica dentro do registro da capacidade, onde o Cleanup enxerga.

O texto fixo de chamada (na skill do Orchestrator) e o AGENTS.md dizem onde fica;
nenhuma instrução manda gravar em /tmp. E a decisão do humano é gravada como ele escreveu.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
AGENTS = RAIZ / ".agents"
ORQ = AGENTS / "skills" / "orchestrator" / "SKILL.md"
RASCUNHO = ".agents/state/<capacidade>/rascunho/"
INSTRUCOES = [RAIZ / "AGENTS.md", *(AGENTS / "skills").glob("*/SKILL.md"), *(AGENTS / "skills").glob("*/references/*.md"),
              *(AGENTS / "shared" / "guias").glob("*.md")]


def texto_de_chamada():
    t = ORQ.read_text(encoding="utf-8")
    return re.search(r"## Chamar um papel.*?```\n(.*?)```", t, re.S).group(1)


def test_texto_de_chamada_diz_onde_fica_o_rascunho():
    assert RASCUNHO in texto_de_chamada()


def test_agents_md_diz_onde_fica_o_rascunho():
    assert RASCUNHO in (RAIZ / "AGENTS.md").read_text(encoding="utf-8")


def test_nenhuma_instrucao_manda_gravar_em_tmp():
    for arq in INSTRUCOES:
        for n, linha in enumerate(arq.read_text(encoding="utf-8").splitlines(), 1):
            if "/tmp" in linha:
                assert "nunca" in linha, f"{arq.relative_to(RAIZ)}:{n}: {linha}"


def test_decisao_do_humano_como_ele_escreveu():
    assert "como ele escreveu" in ORQ.read_text(encoding="utf-8")
