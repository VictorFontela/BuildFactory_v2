"""E2a: a tabela de transições, provada pela sequência do to-do, pelas 7 decisões e por caminhadas aleatórias."""
import copy
import json
import random
import sys
from collections import Counter
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SHARED = Path(__file__).resolve().parents[3] / "shared"
sys.path.insert(0, str(SCRIPTS))
from proximo_estado import MAX_VOLTAS, ForaDeLugar, iniciar, transicao  # noqa: E402

EX = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (SHARED / "exemplos").glob("*.json")}
C = "abc1234"


def ev(tipo, **campos):
    d = copy.deepcopy(EX[tipo])
    d.update(campos)
    return d


def ativ(passo, spec, **decisoes):
    campos = copy.deepcopy(spec["passos"][passo - 1]["campos"])
    for nome, v in decisoes.items():
        campos[nome]["decisao"] = v
    return {"tipo": "ativacao_decidida", "passo": passo, "campos": campos}


def resumo(r):
    if r["acao"] == "chamar":
        return "chamar " + "+".join(p["papel"] for p in r["papeis"])
    if r["acao"] == "decidir":
        return f"decidir ativacao {r['passo']}"
    if r["acao"] == "perguntar":
        return f"perguntar {r['pausa']}"
    if r["acao"] == "aguardar":
        return "aguardar " + "+".join(r["faltam"])
    return f"fim {r['resultado']}"


def rodar(seq, e=None):
    """Aplica a sequência e devolve [(resumo, t, fase)] por evento."""
    saida = []
    for evento in seq:
        if e is None:
            e, r = iniciar(evento)
        else:
            e, r = transicao(e, evento)
        saida.append((resumo(r), e.t, e.fase))
    return e, saida


# --- a sequência do to-do: 19 eventos ---------------------------------------

SPEC = EX["spec_pronta"]
TODO = [
    (EX["capacidade_criada"], ("chamar Specification", 0, "Specification")),
    (SPEC, ("decidir ativacao 1", 0, "Ativacao")),
    (ativ(1, SPEC), ("chamar Tests", 0, "Tests")),
    (ev("testes_red"), ("chamar Backend", 0, "Builders")),
    (ev("build_pronto"), ("chamar Reviewer", 0, "Reviewer")),
    (ev("aprovado", papel="Reviewer", evidencia="2 de 2 testes passam"), ("chamar QA", 0, "QA")),
    (ev("reprovacao"), ("chamar Backend", 1, "Builders")),
    (ev("build_pronto", arquivos=["api/repo/tarefas.py"], resumo="filtro antes do LIMIT/OFFSET"), ("chamar Reviewer", 1, "Reviewer")),
    (ev("aprovado", papel="Reviewer", evidencia="2 de 2 testes passam"), ("chamar QA", 1, "QA")),
    (ev("aprovado"), ("decidir ativacao 2", 0, "Ativacao")),
    (ev("ativacao_decidida"), ("chamar Tests", 0, "Tests")),
    (ev("testes_red", passo=2, arquivos=["web/src/tarefas/Lista.test.tsx"], comando="npm test Lista"), ("chamar Frontend", 0, "Builders")),
    (ev("explorar_solicitado"), ("chamar Explorer", 0, "Explorer")),
    (ev("explorer_resposta"), ("chamar Frontend", 0, "Builders")),
    (ev("build_pronto", passo=2, builder="Frontend", arquivos=["web/src/tarefas/Lista.tsx"]), ("chamar Reviewer", 0, "Reviewer")),
    (ev("aprovado", passo=2, papel="Reviewer", evidencia="3 de 3 testes passam"), ("chamar QA", 0, "QA")),
    (ev("aprovado", passo=2, evidencia="filtro Concluídas mostra as 3 marcadas"), ("chamar DevOps", 0, "DevOps")),
    (ev("devops_decisao"), ("chamar Cleanup", 0, "Cleanup")),
    (ev("limpeza_feita"), ("fim Entregue", 0, "Entregue")),
]


def test_sequencia_todo_19_de_19():
    _, obtido = rodar([x for x, _ in TODO])
    esperado = [y for _, y in TODO]
    assert len(obtido) == 19
    assert obtido == esperado


# --- prefixo comum: capacidade com 1 passo ----------------------------------

def spec1(**campos):
    base = {"interface": {"valor": False}, "servidor": {"valor": True, "trecho": "marcar"},
            "agente_llm": {"valor": False}, "seguranca": {"valor": False}}
    base.update(campos)
    return {"tipo": "spec_pronta", "passos": [{"id": 1, "descricao": "API de status", "criterios": ["concluir muda o status"], "diretorios": ["api/"], "campos": base}]}


def ate_revisao(spec, **dec):
    e, _ = iniciar(EX["capacidade_criada"])
    e, _ = transicao(e, spec)
    e, _ = transicao(e, ativ(1, spec, **dec))
    e, _ = transicao(e, ev("testes_red"))
    for b in list(e.pendentes):
        e, _ = transicao(e, ev("build_pronto", builder=b))
    return e


def rep(papel="Reviewer", destino=("Backend",)):
    return ev("reprovacao", reprovou=papel, destino=list(destino))


# --- as 7 decisões -----------------------------------------------------------

def test_d1_ativacao_decidida_liga_quem_atua():
    s = spec1(interface={"valor": "incerto", "trecho": "lista"}, seguranca={"valor": True, "trecho": "login"})
    e, _ = iniciar(EX["capacidade_criada"])
    e, _ = transicao(e, s)
    e, r = transicao(e, ativ(1, s, interface=True))
    assert e.ativos["1"] == ["Frontend", "Backend"] and e.security["1"] is True
    with pytest.raises(ForaDeLugar, match="difere da spec"):
        outro = ativ(1, s, interface=True)
        outro["campos"]["servidor"]["trecho"] = "trecho inventado"
        transicao(transicao(iniciar(EX["capacidade_criada"])[0], s)[0], outro)


def test_d2_teste_corrigido_volta_a_todos_os_builders():
    s = spec1(interface={"valor": True, "trecho": "tela"})
    e = ate_revisao(s)
    e, r = transicao(e, rep(destino=["Tests"]))
    assert resumo(r) == "chamar Tests" and e.t == 1
    e, r = transicao(e, ev("testes_red"))
    assert resumo(r) == "chamar Frontend+Backend"


def test_d3_mais_uma_volta_vai_para_o_destino_da_ultima():
    e = ate_revisao(spec1(interface={"valor": True, "trecho": "tela"}))
    for destino in (["Backend"], ["Backend"]):
        e, _ = transicao(e, rep(destino=destino))
        e, _ = transicao(e, ev("build_pronto"))
    assert e.t == MAX_VOLTAS
    e, r = transicao(e, rep(destino=["Frontend"]))
    assert resumo(r) == "perguntar Escalar" and len(r["pacote"]["voltas"]) == 2
    e, r = transicao(e, ev("decisao_humana", saida="mais_uma_volta", instrucao="usar o mesmo componente"))
    assert resumo(r) == "chamar Frontend" and r["papeis"][0]["entrada"]["instrucao"]
    assert e.t == MAX_VOLTAS


def test_d4_replanejar_mantem_passos_aprovados():
    spec = copy.deepcopy(SPEC)
    e, _ = rodar([x for x, _ in TODO[:10]])
    e, _ = transicao(e, ativ(2, spec, servidor=False))
    e, _ = transicao(e, ev("duvida_contrato"))
    e, r = transicao(e, ev("decisao_humana", saida="replanejar", instrucao="filtro guarda a escolha"))
    assert resumo(r) == "chamar Specification" and r["papeis"][0]["entrada"]["replanejar_de"] == 2
    mudou = copy.deepcopy(spec)
    mudou["passos"][0]["descricao"] = "API reescrita"
    e2, r = transicao(e, mudou)
    assert "corrigir" in r["papeis"][0]["entrada"] and e2.fase == "Specification"
    novo = copy.deepcopy(spec)
    novo["passos"][1]["descricao"] = "Tela: filtro que lembra a escolha"
    e3, r = transicao(e2, novo)
    assert resumo(r) == "decidir ativacao 2" and e3.passos[0] == e.passos[0]


def test_d5_devops_pausa_e_recusa_escala():
    e, _ = rodar([x for x, _ in TODO[:16]])
    e, r = transicao(e, TODO[16][0])
    assert resumo(r) == "chamar DevOps" and r["depois"] == {"acao": "perguntar", "pausa": "DevOps"}
    e, r = transicao(e, ev("devops_decisao", aprovado=False, motivo="falta o texto do filtro vazio"))
    assert resumo(r) == "perguntar Escalar" and r["pacote"]["recusa_devops"]
    e, r = transicao(e, ev("decisao_humana", saida="mais_uma_volta", instrucao="mostrar 'nenhuma tarefa'"))
    assert resumo(r) == "chamar Frontend"


def test_d6_so_reprovacao_valida_conta_volta():
    e = ate_revisao(spec1())
    e, r = transicao(e, rep(destino=["Frontend"]))
    assert "corrigir" in r["papeis"][0]["entrada"] and e.t == 0 and e.fase == "Reviewer"
    e, _ = transicao(e, ev("duvida_contrato", quem="Reviewer", passo=1))
    e, _ = transicao(e, ev("decisao_humana"))
    e, _ = transicao(e, ev("explorar_solicitado", quem_chamou="Reviewer"))
    e, _ = transicao(e, ev("explorer_resposta"))
    assert e.t == 0 and e.fase == "Reviewer"


def test_d7_dois_builders_aguardam_um_ao_outro():
    s = spec1(interface={"valor": True, "trecho": "tela"})
    e, _ = iniciar(EX["capacidade_criada"])
    e, _ = transicao(e, s)
    e, _ = transicao(e, ativ(1, s))
    e, r = transicao(e, ev("testes_red"))
    assert resumo(r) == "chamar Frontend+Backend"
    e, _ = transicao(e, ev("explorar_solicitado", quem_chamou="Frontend"))
    e, r = transicao(e, ev("build_pronto", builder="Backend"))
    assert resumo(r) == "aguardar Frontend" and e.fase == "Explorer"
    e, r = transicao(e, ev("explorer_resposta"))
    assert resumo(r) == "chamar Frontend"
    e, r = transicao(e, ev("build_pronto", builder="Frontend"))
    assert resumo(r) == "chamar Reviewer"


def test_teto_do_explorer_e_zera_no_passo_seguinte():
    e = ate_revisao(spec1())
    for _ in range(3):
        e, _ = transicao(e, ev("explorar_solicitado", quem_chamou="Reviewer"))
        e, _ = transicao(e, ev("explorer_resposta"))
    e, r = transicao(e, ev("explorar_solicitado", quem_chamou="Reviewer"))
    assert "aviso" in r["papeis"][0]["entrada"] and e.fase == "Reviewer"


@pytest.mark.parametrize("evento,erro", [
    (lambda: ev("aprovado", papel="QA"), "espera aprovado ou reprovacao de Reviewer"),
    (lambda: ev("aprovado", passo=2, papel="Reviewer"), "passo 2"),
    (lambda: ev("build_pronto"), "espera aprovado"),
    (lambda: ev("explorar_solicitado", quem_chamou="Backend"), "não está atuando"),
    (lambda: ev("decisao_humana"), "espera aprovado"),
])
def test_fora_de_lugar_nao_muda_nada(evento, erro):
    e = ate_revisao(spec1())
    antes = e.model_dump()
    with pytest.raises(ForaDeLugar, match=erro):
        transicao(e, evento())
    assert e.model_dump() == antes


# --- caminhadas aleatórias ---------------------------------------------------

def gerar(e, rng):
    """Eventos que os papéis e o humano poderiam emitir agora, inclusive errados no contexto."""
    f, p = e.fase, e.passo
    quem = {"Builders": e.pendentes}.get(f, [f])
    extras = []
    if f in ("Specification", "Tests", "Builders", "Reviewer", "QA", "Security", "DevOps", "Cleanup"):
        q = rng.choice(quem)
        extras = [ev("duvida_contrato", quem=q, passo=p), ev("explorar_solicitado", quem_chamou=q)]
    if f == "Specification":
        n = rng.randint(1, 3)
        passos = copy.deepcopy(e.passos[: (e.replanejar_de or 1) - 1])
        for i in range(len(passos) + 1, max(n, len(passos) + 1) + 1):
            campos = {}
            for nome in ("interface", "servidor", "agente_llm", "seguranca"):
                v = rng.choice([True, False, False, "incerto"])
                campos[nome] = {"valor": v, "trecho": "trecho" if v is not False else ""}
            passos.append({"id": i, "descricao": f"passo {i} da capacidade", "criterios": [f"critério do passo {i}"], "diretorios": ["app/"], "campos": campos})
        return [{"tipo": "spec_pronta", "passos": passos}] * 3 + extras
    if f == "Ativacao":
        campos = copy.deepcopy(e.passos[p - 1]["campos"])
        for c in campos.values():
            if c["valor"] == "incerto":
                c["decisao"] = rng.choice([True, False])
        return [{"tipo": "ativacao_decidida", "passo": p, "campos": campos}]
    if f == "Tests":
        return [ev("testes_red", passo=p)] * 3 + extras
    if f == "Builders":
        return [ev("build_pronto", passo=p, builder=b) for b in e.pendentes] * 3 + extras
    if f in ("Reviewer", "QA", "Security"):
        alvos = e.ativos.get(str(p), []) + ["Tests"]
        destino = rng.sample(alvos, rng.randint(1, len(alvos)))
        errado = [rng.choice([b for b in ("Frontend", "Backend", "AI") if b not in alvos] or ["Tests"])]
        return [ev("aprovado", passo=p, papel=f)] * 3 + [ev("reprovacao", passo=p, reprovou=f, destino=destino)] * 2 \
            + [ev("reprovacao", passo=p, reprovou=f, destino=errado)] + extras
    if f == "Escalar":
        return [ev("decisao_humana", saida=s, instrucao="instrução") for s in ("mais_uma_volta", "mais_uma_volta", "replanejar", "abortar")]
    if f in ("Duvida", "Explorer"):
        base = [ev("decisao_humana", saida=s, instrucao="instrução") for s in ("seguir", "seguir", "replanejar", "abortar")] \
            if f == "Duvida" else [ev("explorer_resposta")]
        r = e.retomar
        outros = [ev("build_pronto", passo=p, builder=b) for b in r.pendentes if b != r.quem] if r.fase == "Builders" else []
        return base * 2 + outros
    if f == "DevOps":
        return [ev("devops_decisao")] * 3 + [ev("devops_decisao", aprovado=False, motivo="falta algo")] + extras
    if f == "Cleanup":
        return [ev("limpeza_feita")]
    return []


def feliz(e):
    """Política que só aprova: de qualquer estado, precisa chegar a Entregue."""
    f, p = e.fase, e.passo
    if f == "Escalar":
        return ev("decisao_humana", saida="mais_uma_volta", instrucao="instrução")
    if f == "Duvida":
        return ev("decisao_humana", saida="seguir", instrucao="instrução")
    if f == "Explorer":
        return ev("explorer_resposta")
    if f in ("Reviewer", "QA", "Security"):
        return ev("aprovado", passo=p, papel=f)
    if f == "DevOps":
        return ev("devops_decisao")
    return [x for x in gerar(e, random.Random(0)) if x["tipo"] not in ("duvida_contrato", "explorar_solicitado")][0]


def chega_ao_fim(e, limite=200):
    for _ in range(limite):
        if e.fase in ("Entregue", "Falhou"):
            return e.fase
        e, _ = transicao(e, feliz(e))
    return None


def test_1000_caminhadas_sem_beco_e_sem_estourar_voltas():
    visitas, fins = Counter(), Counter()
    for semente in range(1000):
        rng = random.Random(semente)
        e, _ = iniciar(EX["capacidade_criada"])
        for passo in range(300):
            if e.fase in ("Entregue", "Falhou"):
                break
            if passo % 7 == 0:
                assert chega_ao_fim(e) == "Entregue", f"semente {semente}: sem caminho até Entregue a partir de {e.fase}"
            evento = rng.choice(gerar(e, rng))
            visitas[(e.fase, evento["tipo"])] += 1
            e, r = transicao(e, evento)
            assert 0 <= e.t <= MAX_VOLTAS
            assert r["acao"] in ("chamar", "aguardar", "decidir", "perguntar", "fim")
            if r["acao"] == "chamar":
                assert r["papeis"]
        fins[e.fase] += 1
    print("\nfins:", dict(fins))
    print("pares (fase, evento) percorridos:", len(visitas))
    for k, v in sorted(visitas.items()):
        print(f"  {k[0]:13} {k[1]:20} {v}")
    assert fins["Entregue"] > 0 and fins["Falhou"] > 0


def test_security_so_quando_ativo():
    s = spec1(seguranca={"valor": True, "trecho": "login"})
    e = ate_revisao(s)
    e, _ = transicao(e, ev("aprovado", papel="Reviewer"))
    e, r = transicao(e, ev("aprovado", papel="QA"))
    assert resumo(r) == "chamar Security"
    e, r = transicao(e, ev("aprovado", papel="Security"))
    assert resumo(r) == "chamar DevOps"
