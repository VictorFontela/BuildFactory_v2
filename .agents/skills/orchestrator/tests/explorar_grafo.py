"""Percorre o grafo desdobrado da tabela de transições e confere as propriedades do fluxo.

O grafo desenhado tem 14 fases; o de verdade tem um nó por estado completo (fase, passo, t,
ativos, pendentes, retomar, contadores do Explorer…). Aqui, cada estado alcançável recebe todos
os eventos do universo da configuração, certos e errados, e o resultado vira uma aresta.

Um monitor, escrito sem olhar a implementação, acompanha cada caminho: o que foi aprovado no
passo desde o último build ou testes_red. Ele entra na chave da busca, então as propriedades de
caminho (P4) valem para todos os caminhos, não só para os que um teste escolheu.
"""
import copy
import json
import os
import sys
from collections import Counter, deque
from itertools import product
from pathlib import Path

SCRIPTS = Path(os.environ.get("EXPLORAR_SCRIPTS", Path(__file__).resolve().parents[1] / "scripts"))
SHARED = Path(__file__).resolve().parents[3] / "shared"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SHARED))
from eventos import validar  # noqa: E402
from estado import Fase  # noqa: E402
from proximo_estado import BUILDERS, MAX_VOLTAS, REVISORES, TETO_EXPLORER, ForaDeLugar, iniciar, transicao  # noqa: E402

FASES = set(Fase.__args__)
ACOES = {"chamar", "aguardar", "decidir", "perguntar", "fim"}
C = "abc1234"
CAMPO_ATOR = {"interface": "Frontend", "servidor": "Backend", "agente_llm": "AI", "seguranca": "Security"}
PEDEM = ("Specification", "Tests", "Frontend", "Backend", "AI", "Reviewer", "QA", "Security", "DevOps", "Cleanup")


def campos(**valores):
    """campos(servidor=True, seguranca="incerto") → os 4 campos no formato da spec."""
    out = {}
    for nome in CAMPO_ATOR:
        v = valores.get(nome, False)
        out[nome] = {"valor": v, "trecho": "" if v is False else f"trecho de {nome}", "decisao": None}
    return out


def spec(*passos):
    return {"tipo": "spec_pronta", "passos": [
        {"id": i, "descricao": f"passo número {i}", "criterios": [f"critério do passo {i}"],
         "diretorios": ["app/"], "campos": c} for i, c in enumerate(passos, 1)]}


CONFIGS = {
    "c1-dois-passos": {"spec": spec(campos(servidor=True), campos(interface=True, agente_llm=True, seguranca=True)),
                       "explorer": ("Backend",)},
    "c2-incertos": {"spec": spec(campos(servidor="incerto", seguranca="incerto")), "explorer": ()},
    "c3-sem-builder": {"spec": spec(campos()), "explorer": ("Tests",)},
    "c4-explorer": {"spec": spec(campos(servidor=True)), "explorer": ("Backend", "Reviewer")},
}


def destinos(c):
    """Um builder do passo, o Tests, um builder que não atua e, com mais de um, todos os do passo."""
    possiveis = [CAMPO_ATOR[k] for k, v in c.items() if v["valor"] is not False and k != "seguranca"]
    fora = [b for b in BUILDERS if b not in possiveis]
    out = [["Tests"]] + ([[possiveis[0]]] if possiveis else []) + ([[fora[0]]] if fora else [])
    return out + ([possiveis] if len(possiveis) > 1 else [])


def universo(cfg):
    """Todos os eventos da configuração, já validados (o formato é conferido uma vez só)."""
    s = cfg["spec"]
    n = len(s["passos"])
    ev = []

    def add(d):
        ev.append(validar(d))

    add(s)
    alterada = copy.deepcopy(s)
    alterada["passos"][0]["descricao"] = "passo um mudado"
    add(alterada)
    if n > 1:
        add({**s, "passos": s["passos"][:1]})
    for p in range(1, n + 2):
        c = s["passos"][min(p, n) - 1]["campos"]
        incertos = [k for k, v in c.items() if v["valor"] == "incerto"]
        for combo in product((True, False), repeat=len(incertos)):
            d = copy.deepcopy(c)
            for k, v in zip(incertos, combo):
                d[k]["decisao"] = v
            add({"tipo": "ativacao_decidida", "passo": p, "campos": d})
        mexido = copy.deepcopy(c)
        mexido["interface"] = {"valor": True, "trecho": "outro", "decisao": None} if c["interface"]["valor"] is False \
            else {"valor": False, "trecho": "", "decisao": None}
        for k, v in mexido.items():
            if v["valor"] == "incerto":
                v["decisao"] = True
        add({"tipo": "ativacao_decidida", "passo": p, "campos": mexido})
        add({"tipo": "testes_red", "passo": p, "arquivos": ["tests/test_x.py"], "comando": "pytest",
             "falhas": ["test_x: assert falhou"], "commit": C})
        for b in BUILDERS:
            add({"tipo": "build_pronto", "passo": p, "builder": b, "arquivos": ["app/x.py"],
                 "resumo": "o passo funciona", "commit": C})
        for r in REVISORES:
            add({"tipo": "aprovado", "passo": p, "papel": r, "evidencia": "testes passam"})
            for destino in destinos(c):
                add({"tipo": "reprovacao", "passo": p, "reprovou": r, "motivo": "app/x.py:1 defeito",
                     "arquivos": ["app/x.py"], "destino": destino, "porque": "o defeito vem dali"})
    for saida in ("mais_uma_volta", "replanejar", "abortar", "seguir"):
        add({"tipo": "decisao_humana", "saida": saida, "instrucao": "faça assim"})
    add({"tipo": "devops_decisao", "aprovado": True})
    add({"tipo": "devops_decisao", "aprovado": False, "motivo": "não pode subir"})
    add({"tipo": "limpeza_feita", "removidos": [], "mantidos": [".agents/state/ — registro"]})
    add({"tipo": "explorer_resposta", "achados": [], "nao_achou": True})
    add({"tipo": "capacidade_criada", "capacidade": "x", "pedido": "outro pedido"})
    for quem in PEDEM:
        add({"tipo": "duvida_contrato", "quem": quem, "pergunta": "qual regra vale?", "por_que_muda": "muda o resultado"})
    for quem in cfg["explorer"]:
        add({"tipo": "explorar_solicitado", "quem_chamou": quem, "pergunta": "onde está isso?",
             "escopo": ["app/"], "para_que": "seguir o padrão"})
    return ev


# --- monitor: o que foi aprovado no passo desde o último build ---------------------

def ultimo_revisor(e, passo):
    return "Security" if e.security.get(str(passo)) else "QA"


def monitorar(e0, ev, e1, mon, falhas):
    """mon = (passo, etapa, liberado): etapa em build, Reviewer, QA, Security; liberado = o humano aprovou no DevOps."""
    passo, etapa, liberado = mon
    if ev.tipo in ("testes_red", "build_pronto"):
        etapa = "build"
    elif ev.tipo == "aprovado":
        antes = {"Reviewer": "build", "QA": "Reviewer", "Security": "QA"}[ev.papel]
        if etapa != antes:
            falhas["P4"].append(f"{ev.papel} aprovou o passo {e0.passo} com etapa {etapa}")
        etapa = ev.papel
    troca = e1.passo != e0.passo and e0.passo is not None and e1.passo == e0.passo + 1
    devops = e1.fase == "DevOps" and e0.fase != "DevOps"
    if troca or devops:
        if etapa != ultimo_revisor(e0, e0.passo):
            falhas["P4"].append(f"saiu do passo {e0.passo} para {e1.fase}/{e1.passo} com etapa {etapa}")
    if e1.passo != passo:
        passo, etapa = e1.passo, "inicio"
    if e0.fase == "DevOps" and ev.tipo == "devops_decisao" and ev.aprovado:
        liberado = True
    if e1.fase == "Cleanup" and not liberado:
        falhas["P5"].append(f"chegou ao Cleanup por {ev.tipo} a partir de {e0.fase} sem o ok do humano no DevOps")
    return passo, etapa, liberado


def chave(e, mon):
    """O conteúdo de `voltas` não decide nenhuma seta (só vai no pacote para o humano): a chave guarda quantas são."""
    return e.model_dump_json(exclude={"seq", "voltas"}) + json.dumps([len(e.voltas), mon])


def explorar(nome, limite=200_000, parar=False):
    """parar=True termina na primeira violação (usado para conferir que um defeito plantado é acusado)."""
    cfg = CONFIGS[nome]
    eventos = universo(cfg)
    falhas = {f"P{i}": [] for i in (1, "2a", "2b", 3, 4, 5, 6, 7, 8, 9, 10)} | {"limite": []}
    e0, r0 = iniciar(validar({"tipo": "capacidade_criada", "capacidade": "verificacao", "pedido": "pedido de teste"}))
    inicio = (e0, (None, "inicio", False))
    nos = {chave(*inicio): inicio}
    arestas = {}  # chave origem → set de chaves destino
    fila = deque([chave(*inicio)])
    fases, acoes = Counter([e0.fase]), Counter([r0["acao"]])
    recusas = amostra = 0
    while fila:
        k = fila.popleft()
        e, mon = nos[k]
        antes = e.model_dump_json()
        saida = arestas.setdefault(k, set())
        for ev in eventos:
            try:
                e1, r = transicao(e, ev)
            except ForaDeLugar:
                recusas += 1
                if e.model_dump_json() != antes:
                    falhas["P7"].append(f"{ev.tipo} recusado alterou o estado em {e.fase}")
                continue
            except Exception as x:  # noqa: BLE001
                falhas["P1"].append(f"{e.fase} + {ev.tipo}: {type(x).__name__}: {x}")
                continue
            amostra += 1
            if amostra % 10 == 0:  # P9 numa amostra fixa de 1 em cada 10 arestas
                e2, r2 = transicao(e, ev)
                if e2.model_dump_json() != e1.model_dump_json() or r2 != r:
                    falhas["P9"].append(f"{e.fase} + {ev.tipo} deu dois resultados")
            conferir_aresta(e, ev, e1, r, falhas)
            mon1 = monitorar(e, ev, e1, mon, falhas)
            if parar and any(falhas.values()):
                fila.clear()
                break
            fases[e1.fase] += 1
            acoes[r["acao"]] += 1
            k1 = chave(e1, mon1)
            saida.add(k1)
            if k1 not in nos:
                if len(nos) >= limite:
                    falhas["limite"].append(f"{nome}: mais de {limite} estados; busca interrompida")
                    fila.clear()
                    break
                nos[k1] = (e1, mon1)
                fila.append(k1)
    if falhas["limite"] or (parar and any(falhas.values())):
        return {"config": nome, "estados": len(nos), "falhas": {k: v for k, v in falhas.items() if v}}
    # P2: de todo estado, um fim é alcançável (busca para trás a partir dos fins)
    reverso = {}
    for a, ds in arestas.items():
        for b in ds:
            reverso.setdefault(b, set()).add(a)
    for alvo, prop, considerar in (({"Entregue", "Falhou"}, "P2a", lambda e: True),
                                   ({"Entregue"}, "P2b", lambda e: e.fase != "Falhou")):
        chega = {k for k, (e, _) in nos.items() if e.fase in alvo}
        pilha = list(chega)
        while pilha:
            for a in reverso.get(pilha.pop(), ()):
                if a not in chega:
                    chega.add(a)
                    pilha.append(a)
        presos = [nos[k][0].fase for k in nos if k not in chega and considerar(nos[k][0])]
        if presos:
            falhas[prop].append(f"{len(presos)} estados sem caminho até {sorted(alvo)}: {Counter(presos).most_common(5)}")
    n_arestas = sum(len(v) for v in arestas.values())
    return {"config": nome, "eventos": len(eventos), "estados": len(nos), "arestas": n_arestas,
            "recusas": recusas, "fases": dict(fases), "acoes": dict(acoes),
            "falhas": {k: v for k, v in falhas.items() if v}}


def conferir_aresta(e, ev, e1, r, falhas):
    if e1.t > MAX_VOLTAS:
        falhas["P3"].append(f"t = {e1.t} em {e1.fase}")
    if ev.tipo == "reprovacao":
        corrigir = r["acao"] == "chamar" and r["papeis"][0]["papel"] == e.fase
        if corrigir:
            if e1.t != e.t or e1.fase != e.fase:
                falhas["P3"].append(f"destino inválido mudou t ({e.t} → {e1.t}) ou fase ({e1.fase})")
        elif e.t >= MAX_VOLTAS:
            if e1.fase != "Escalar" or r["acao"] != "perguntar":
                falhas["P3"].append(f"reprovação com t={e.t} levou a {e1.fase}/{r['acao']}")
        elif e1.t != e.t + 1 or e1.fase not in ("Builders", "Tests"):
            falhas["P3"].append(f"reprovação com t={e.t} levou a {e1.fase} com t={e1.t}")
    if e1.fase == "Entregue" and not (e.fase == "Cleanup" and ev.tipo == "limpeza_feita"):
        falhas["P5"].append(f"chegou a Entregue por {ev.tipo} a partir de {e.fase}")
    if e.fase in ("Explorer", "Duvida") and e1.fase not in ("Explorer", "Duvida") and \
            (ev.tipo == "explorer_resposta" or (ev.tipo == "decisao_humana" and ev.saida == "seguir")):
        chamado = r["papeis"][0]["papel"] if r["acao"] == "chamar" else None
        if e1.fase != e.retomar.fase or chamado != e.retomar.quem:
            falhas["P6"].append(f"desvio de {e.retomar.quem}/{e.retomar.fase} voltou para {chamado}/{e1.fase}")
    if any(v > TETO_EXPLORER for v in e1.explorer.values()):
        falhas["P8"].append(f"contador do Explorer passou de {TETO_EXPLORER}: {e1.explorer}")
    if ev.tipo == "explorar_solicitado" and e1.fase != "Explorer" and r["acao"] == "chamar":
        if r["papeis"][0]["papel"] != ev.quem_chamou or "aviso" not in r["papeis"][0]["entrada"]:
            falhas["P8"].append(f"pedido ao Explorer além do teto não voltou com aviso para {ev.quem_chamou}")
    if r["acao"] == "chamar" and any(p["papel"] == "Reviewer" for p in r["papeis"]) and e1.fase == "Reviewer":
        if e1.pendentes or any(b not in e1.builds for b in e1.ativos.get(str(e1.passo), [])):
            falhas["P10"].append(f"Reviewer chamado com pendentes {e1.pendentes} e builds {sorted(e1.builds)}")


def verificar_tudo():
    resultados = [explorar(n) for n in CONFIGS]
    fases = set().union(*(r["fases"] for r in resultados)) | {"Specification"}
    acoes = set().union(*(r["acoes"] for r in resultados))
    cobertura = {"fases_faltando": sorted(FASES - fases), "acoes_faltando": sorted(ACOES - acoes)}
    return resultados, cobertura


if __name__ == "__main__":
    import time
    t0 = time.time()
    resultados, cobertura = verificar_tudo()
    print(json.dumps({"configs": resultados, "cobertura": cobertura, "segundos": round(time.time() - t0, 1)},
                     ensure_ascii=False, indent=1))
