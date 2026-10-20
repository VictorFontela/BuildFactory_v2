"""E13: as propriedades do fluxo valem em todo estado alcançável, não só nos caminhos que um teste escolheu.

A busca completa está em explorar_grafo.py. Aqui roda nas configurações que cabem na suíte;
as outras rodam com `python explorar_grafo.py`.
"""
import pytest

import explorar_grafo as g

RAPIDAS = ["c3-sem-builder", "c2-incertos"]


@pytest.fixture(scope="module", params=RAPIDAS)
def resultado(request):
    return g.explorar(request.param)


def test_nenhuma_propriedade_violada(resultado):
    assert resultado["falhas"] == {}, {k: v[:3] for k, v in resultado["falhas"].items()}


def test_a_busca_percorre_o_grafo_desdobrado(resultado):
    assert resultado["estados"] > 1000 and resultado["arestas"] > resultado["estados"]


def test_o_monitor_pega_uma_tabela_que_pula_o_qa(monkeypatch):
    original = g.transicao

    def pula_qa(e, ev):
        e1, r = original(e, ev)
        if e1.fase == "QA":
            e1, r = original(e1, g.validar({"tipo": "aprovado", "passo": e1.passo, "papel": "QA",
                                             "evidencia": "aprovado sem rodar"}))
        return e1, r

    monkeypatch.setattr(g, "transicao", pula_qa)
    falhas = g.explorar("c3-sem-builder")["falhas"]
    assert falhas.get("P4"), "o monitor deveria acusar a saída do passo sem a aprovação do QA registrada"


def test_o_monitor_pega_uma_tabela_que_sobe_sem_o_humano(monkeypatch):
    original = g.transicao

    def sem_humano(e, ev):
        e1, r = original(e, ev)
        if e1.fase == "DevOps":
            e1 = e1.model_copy(update={"fase": "Cleanup"})
        return e1, r

    monkeypatch.setattr(g, "transicao", sem_humano)
    assert g.explorar("c3-sem-builder")["falhas"].get("P5")
