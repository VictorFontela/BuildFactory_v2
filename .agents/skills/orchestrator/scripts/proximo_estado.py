"""Tabela de transições do fluxo.

`iniciar(evento)` e `transicao(estado, evento)` devolvem (novo estado, resposta).
Nenhuma das duas lê ou grava arquivo; o comando, no fim deste arquivo, grava
em .agents/state/<capacidade>/ (ver estado.py). A resposta é uma de cinco ações:

    chamar     papéis a chamar agora, cada um com sua entrada
    aguardar   faltam builders do mesmo passo entregarem
    decidir    o Orchestrator decide a ativação do passo (campos incerto)
    perguntar  pausa para o humano (Escalar, Duvida ou DevOps)
    fim        Entregue ou Falhou

Evento que não cabe no estado atual levanta ForaDeLugar e nada muda: é erro de
quem entregou o evento, não do papel. Evento que cabe mas está errado no
contexto (destino que não atua no passo, passo aprovado alterado no replanejar)
volta como `chamar` para quem o emitiu corrigir, sem contar volta.
"""
import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parents[2] / "shared"))
from eventos import validar  # noqa: E402
from estado import Estado, Retomar, carregar, gravar_json, pasta, salvar  # noqa: E402
from montar_saida import decidir  # noqa: E402

MAX_VOLTAS = 2
TETO_EXPLORER = 3
BUILDERS = ("Frontend", "Backend", "AI")
REVISORES = ("Reviewer", "QA", "Security")


class ForaDeLugar(Exception):
    pass


def _d(ev):
    return ev.model_dump(mode="json")


def _chamar(*pares, **extra):
    return {"acao": "chamar", "papeis": [{"papel": p, "entrada": e} for p, e in pares], **extra}


def _fim(e, resultado):
    e.fase = resultado
    return e, {"acao": "fim", "resultado": resultado}


def _ativos(e):
    return e.ativos.get(str(e.passo), [])


def _esperados(e):
    if e.fase == "Builders":
        return set(e.pendentes)
    if e.fase in ("Specification", "Tests", "DevOps", "Cleanup") + REVISORES:
        return {e.fase}
    return set()


def _entrada(e, papel):
    if papel == "Specification":
        return {"capacidade": e.capacidade, "pedido": e.pedido}
    if papel == "DevOps":
        return {"capacidade": e.capacidade, "passos": len(e.passos)}
    if papel == "Cleanup":
        return {"capacidade": e.capacidade}
    d = {"capacidade": e.capacidade, "pedido": e.pedido, "passo": e.passo, "spec": e.passos[e.passo - 1]}
    if papel == "Tests":
        d["builders"] = _ativos(e)
    if papel in BUILDERS:
        d["testes_red"] = e.testes
    if papel in REVISORES:
        d["testes_red"] = e.testes
        d["builds"] = [e.builds[b] for b in BUILDERS if b in e.builds]
    return d


def _ir(e, fase):
    e.fase = fase
    return e, _chamar((fase, _entrada(e, fase)))


def _abrir_passo(e, n):
    e.passo, e.t, e.voltas, e.destino_ultima = n, 0, [], []
    e.testes, e.builds, e.pendentes = None, {}, []
    e.fase = "Ativacao"
    return e, {"acao": "decidir", "o_que": "ativacao", "passo": n, "campos": e.passos[n - 1]["campos"]}


def _reabrir(e, destino, extra):
    if "Tests" in destino:
        e.fase = "Tests"
        return e, _chamar(("Tests", {**_entrada(e, "Tests"), **extra}))
    e.fase = "Builders"
    e.pendentes = [b for b in BUILDERS if b in destino]
    return e, _chamar(*[(b, {**_entrada(e, b), **extra}) for b in e.pendentes])


def _avancar(e):
    if e.passo < len(e.passos):
        return _abrir_passo(e, e.passo + 1)
    e.fase = "DevOps"
    return e, _chamar(("DevOps", _entrada(e, "DevOps")), depois={"acao": "perguntar", "pausa": "DevOps"})


def _replanejar(e, instrucao):
    n = e.passo or 1
    e.replanejar_de, e.fase = n, "Specification"
    return e, _chamar(("Specification", {**_entrada(e, "Specification"), "replanejar_de": n,
                                          "voltas": e.voltas, "instrucao": instrucao}))


def _escalar(e, pacote):
    e.fase = "Escalar"
    return e, {"acao": "perguntar", "pausa": "Escalar",
               "pacote": {"passo": e.passo, "voltas": e.voltas, **pacote,
                          "saidas": ["mais_uma_volta", "replanejar", "abortar"]}}


def _mesmo_passo(e, ev):
    if ev.passo != e.passo:
        raise ForaDeLugar(f"evento do passo {ev.passo}, mas o fluxo está no passo {e.passo}")


# --- por fase -------------------------------------------------------------

def _spec(e, ev):
    if ev.tipo != "spec_pronta":
        raise ForaDeLugar(f"{e.fase} espera spec_pronta, veio {ev.tipo}")
    passos = [p.model_dump(mode="json") for p in ev.passos]
    n = e.replanejar_de or 1
    if passos[: n - 1] != e.passos[: n - 1]:
        return e, _chamar(("Specification", {**_entrada(e, "Specification"), "replanejar_de": n,
                           "corrigir": f"os passos 1 a {n - 1} já foram aprovados e precisam continuar iguais"}))
    if len(passos) < n:
        return e, _chamar(("Specification", {**_entrada(e, "Specification"), "replanejar_de": n,
                           "corrigir": f"a spec precisa ter o passo {n} em diante"}))
    e.passos, e.replanejar_de = passos, None
    return _abrir_passo(e, n)


def _ativacao(e, ev):
    if ev.tipo != "ativacao_decidida":
        raise ForaDeLugar(f"Ativacao espera ativacao_decidida, veio {ev.tipo}")
    _mesmo_passo(e, ev)
    campos = ev.campos.model_dump(mode="json")
    spec = e.passos[e.passo - 1]["campos"]
    for nome, c in campos.items():
        if (c["valor"], c["trecho"]) != (spec[nome]["valor"], spec[nome]["trecho"]):
            raise ForaDeLugar(f"campo {nome} difere da spec: só a decisão do incerto pode ser acrescentada")
    ativos = decidir(campos)
    e.ativos[str(e.passo)] = [b for b in BUILDERS if b in ativos]
    e.security[str(e.passo)] = "Security" in ativos
    return _ir(e, "Tests")


def _tests(e, ev):
    if ev.tipo != "testes_red":
        raise ForaDeLugar(f"Tests espera testes_red, veio {ev.tipo}")
    _mesmo_passo(e, ev)
    e.testes = _d(ev)
    if not _ativos(e):
        return _ir(e, "Reviewer")
    e.fase, e.pendentes = "Builders", list(_ativos(e))
    return e, _chamar(*[(b, _entrada(e, b)) for b in e.pendentes])


def _build(e, ev, pendentes):
    _mesmo_passo(e, ev)
    if ev.builder not in pendentes:
        raise ForaDeLugar(f"{ev.builder} não tem entrega pendente neste passo")
    e.builds[ev.builder] = _d(ev)
    pendentes.remove(ev.builder)


def _builders(e, ev):
    if ev.tipo != "build_pronto":
        raise ForaDeLugar(f"Builders espera build_pronto, veio {ev.tipo}")
    _build(e, ev, e.pendentes)
    if e.pendentes:
        return e, {"acao": "aguardar", "faltam": list(e.pendentes)}
    return _ir(e, "Reviewer")


def _revisao(e, ev):
    if ev.tipo == "aprovado" and ev.papel == e.fase:
        _mesmo_passo(e, ev)
        if e.fase == "Reviewer":
            return _ir(e, "QA")
        if e.fase == "QA" and e.security.get(str(e.passo)):
            return _ir(e, "Security")
        return _avancar(e)
    if ev.tipo == "reprovacao" and ev.reprovou == e.fase:
        _mesmo_passo(e, ev)
        possiveis = set(_ativos(e)) | {"Tests"}
        fora = [x for x in ev.destino if x not in possiveis]
        if fora:
            return e, _chamar((e.fase, {**_entrada(e, e.fase), "corrigir":
                               f"destino {fora} não atua neste passo; possíveis: {sorted(possiveis)}"}))
        e.destino_ultima = list(ev.destino)
        if e.t >= MAX_VOLTAS:
            return _escalar(e, {"ultima": _d(ev)})
        e.t += 1
        e.voltas.append(_d(ev))
        return _reabrir(e, ev.destino, {"reprovacao": _d(ev)})
    raise ForaDeLugar(f"{e.fase} espera aprovado ou reprovacao de {e.fase}, veio {ev.tipo}")


def _escalar_decisao(e, ev):
    if ev.tipo != "decisao_humana" or ev.saida == "seguir":
        raise ForaDeLugar("Escalar espera decisao_humana: mais_uma_volta, replanejar ou abortar")
    if ev.saida == "mais_uma_volta":
        return _reabrir(e, e.destino_ultima, {"instrucao": ev.instrucao})
    if ev.saida == "replanejar":
        return _replanejar(e, ev.instrucao)
    return _fim(e, "Falhou")


def _devops(e, ev):
    if ev.tipo != "devops_decisao":
        raise ForaDeLugar(f"DevOps espera devops_decisao, veio {ev.tipo}")
    if ev.aprovado:
        return _ir(e, "Cleanup")
    e.destino_ultima = list(_ativos(e)) or ["Tests"]
    return _escalar(e, {"recusa_devops": ev.motivo})


def _cleanup(e, ev):
    if ev.tipo != "limpeza_feita":
        raise ForaDeLugar(f"Cleanup espera limpeza_feita, veio {ev.tipo}")
    return _fim(e, "Entregue")


# --- dúvida e Explorer, de qualquer fase ------------------------------------

def _pausar(e, ev, quem, fase):
    if quem not in _esperados(e):
        raise ForaDeLugar(f"{quem} não está atuando agora ({e.fase})")
    e.retomar = Retomar(fase=e.fase, quem=quem, pendentes=list(e.pendentes))
    e.fase = fase


def _duvida(e, ev):
    _pausar(e, ev, ev.quem, "Duvida")
    return e, {"acao": "perguntar", "pausa": "Duvida", "pacote": _d(ev)}


def _explorar(e, ev):
    chave = f"{e.passo or 0}:{ev.quem_chamou}"
    if ev.quem_chamou in _esperados(e) and e.explorer.get(chave, 0) >= TETO_EXPLORER:
        return e, _chamar((ev.quem_chamou, {**_entrada(e, ev.quem_chamou), "aviso":
                           f"teto de {TETO_EXPLORER} pedidos ao Explorer neste passo: decida com o que tem ou reprove"}))
    _pausar(e, ev, ev.quem_chamou, "Explorer")
    e.explorer[chave] = e.explorer.get(chave, 0) + 1
    return e, _chamar(("Explorer", {"pedido": _d(ev)}))


def _retomar(e, extra):
    r = e.retomar
    e.fase, e.pendentes, e.retomar = r.fase, list(r.pendentes), None
    return e, _chamar((r.quem, {**_entrada(e, r.quem), **extra}))


def _em_pausa(e, ev):
    r = e.retomar
    if ev.tipo == "build_pronto" and r.fase == "Builders" and ev.builder != r.quem:
        _build(e, ev, r.pendentes)
        return e, {"acao": "aguardar", "faltam": list(r.pendentes)}
    if e.fase == "Explorer":
        if ev.tipo != "explorer_resposta":
            raise ForaDeLugar(f"Explorer espera explorer_resposta, veio {ev.tipo}")
        return _retomar(e, {"explorer_resposta": _d(ev)})
    if ev.tipo != "decisao_humana" or ev.saida == "mais_uma_volta":
        raise ForaDeLugar("Duvida espera decisao_humana: seguir, replanejar ou abortar")
    if ev.saida == "seguir":
        return _retomar(e, {"instrucao": ev.instrucao})
    e.retomar = None
    if ev.saida == "replanejar":
        return _replanejar(e, ev.instrucao)
    return _fim(e, "Falhou")


POR_FASE = {"Specification": _spec, "Ativacao": _ativacao, "Tests": _tests, "Builders": _builders,
            "Reviewer": _revisao, "QA": _revisao, "Security": _revisao, "Escalar": _escalar_decisao,
            "DevOps": _devops, "Cleanup": _cleanup}


def iniciar(evento):
    ev = validar(evento, "capacidade_criada") if isinstance(evento, dict) else evento
    e = Estado(capacidade=ev.capacidade, pedido=ev.pedido, fase="Specification")
    return e, _chamar(("Specification", _entrada(e, "Specification")))


def transicao(estado: Estado, evento):
    e = estado.model_copy(deep=True)
    ev = validar(evento) if isinstance(evento, dict) else evento
    if e.fase in ("Entregue", "Falhou"):
        raise ForaDeLugar(f"capacidade já terminou: {e.fase}")
    if ev.tipo == "capacidade_criada":
        raise ForaDeLugar("capacidade já iniciada")
    if e.fase in ("Explorer", "Duvida"):
        return _em_pausa(e, ev)
    if ev.tipo == "duvida_contrato":
        return _duvida(e, ev)
    if ev.tipo == "explorar_solicitado":
        return _explorar(e, ev)
    return POR_FASE[e.fase](e, ev)


# --- o comando ---------------------------------------------------------------

USO = """uso:
  proximo_estado.py --capacidade <nome> --iniciar "<pedido>"
  proximo_estado.py --capacidade <nome> --evento <arquivo.json>
  proximo_estado.py --capacidade <nome>        (mostra a última resposta: onde o fluxo está)

saída 0: ok, a resposta vai no stdout. 1: evento inválido. 2: uso errado ou JSON ilegível.
3: evento fora de lugar (nada foi gravado). 4: capacidade inexistente ou já iniciada."""


class Saida(Exception):
    def __init__(self, codigo, msg):
        super().__init__(msg)
        self.codigo = codigo


def _validar(dados):
    try:
        return validar(dados)
    except Exception as err:
        linhas = [f"- {'.'.join(str(x) for x in e['loc']) or '(evento)'}: {e['msg']}" for e in err.errors()] \
            if hasattr(err, "errors") else [str(err)]
        raise Saida(1, "evento inválido:\n" + "\n".join(linhas))


def _ler(arquivo):
    caminho = Path(arquivo)
    if not caminho.is_file():
        raise Saida(2, f"arquivo não encontrado: {arquivo}")
    texto = caminho.read_text(encoding="utf-8")
    if texto.lstrip().startswith("```"):
        raise Saida(2, "o arquivo começa com ```: grave só o JSON, sem a cerca de markdown")
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as err:
        raise Saida(2, f"JSON ilegível na linha {err.lineno}, coluna {err.colno}: {err.msg}")
    if not isinstance(dados, dict):
        raise Saida(2, "o evento precisa ser um objeto JSON")
    return _validar(dados)


def _rel(raiz, caminho):
    return str(Path(caminho).relative_to(raiz))


def _saida(raiz, e, quem, sufixo="json"):
    e.seq += 1
    return _rel(raiz, pasta(raiz, e.capacidade) / "saidas" / f"{e.seq:04d}-{quem}.{sufixo}")


def _gravar_rodada(raiz, e, ev, r):
    """Grava o evento, as entradas e a resposta; o estado.json por último, porque é ele que confirma a rodada."""
    base = pasta(raiz, e.capacidade)
    e.seq += 1
    gravar_json(base / "eventos" / f"{e.seq:04d}-{ev.tipo}.json", ev.model_dump(mode="json"))
    if r["acao"] == "chamar":
        for p in r["papeis"]:
            e.seq += 1
            nome = f"{e.seq:04d}-{p['papel'].lower()}"
            gravar_json(base / "entradas" / f"{nome}.json", p["entrada"])
            p["entrada"] = _rel(raiz, base / "entradas" / f"{nome}.json")
            if p["papel"] == "DevOps":
                p["pacote_em"] = _rel(raiz, base / "saidas" / f"{nome}-pacote.md")
            else:
                p["evento_em"] = _rel(raiz, base / "saidas" / f"{nome}.json")
        if "depois" in r:
            r["depois"]["evento_em"] = _saida(raiz, e, "humano")
            r["depois"]["tipo_esperado"] = "devops_decisao"
    elif r["acao"] == "decidir":
        r["evento_em"], r["tipo_esperado"] = _saida(raiz, e, "orchestrator"), "ativacao_decidida"
    elif r["acao"] == "perguntar":
        r["evento_em"], r["tipo_esperado"] = _saida(raiz, e, "humano"), "decisao_humana"
    (base / "saidas").mkdir(parents=True, exist_ok=True)
    gravar_json(base / "ultima_resposta.json", r)
    salvar(raiz, e)
    return r


def _conferir_limpeza(raiz, base, capacidade, removidos):
    """O Cleanup só apaga o que a capacidade criou fora do registro: confere cada removido contra a linha de base."""
    linha = base / "baseline-suite.json"
    if not linha.is_file():
        raise Saida(1, f"limpeza recusada, nada foi gravado: sem linha de base em {_rel(raiz, linha)}")
    antes = set(json.loads(linha.read_text(encoding="utf-8")).get("fora_do_git", []))
    rascunho = f".agents/state/{capacidade}/rascunho"
    erros = []
    for c in removidos:
        limpo = c.rstrip("/")
        if c in antes or limpo in antes or limpo + "/" in antes:
            erros.append(f"{c}: já existia antes da capacidade")
        elif limpo.startswith(".agents/state") and not (limpo == rascunho or limpo.startswith(rascunho + "/")):
            erros.append(f"{c}: é do registro da capacidade")
        elif (raiz / limpo).exists():
            erros.append(f"{c}: continua lá")
    if erros:
        raise Saida(1, "limpeza recusada, nada foi gravado:\n" + "\n".join(f"- {x}" for x in erros))


def executar(args, raiz):
    raiz = Path(raiz).resolve()
    if not args.capacidade:
        raise Saida(2, USO)
    base = pasta(raiz, args.capacidade)
    if args.iniciar is not None:
        if (base / "estado.json").exists():
            raise Saida(4, f"capacidade {args.capacidade!r} já iniciada em {_rel(raiz, base)}")
        ev = _validar({"tipo": "capacidade_criada", "capacidade": args.capacidade, "pedido": args.iniciar})
        e, r = iniciar(ev)
        return _gravar_rodada(raiz, e, ev, r)
    if not (base / "estado.json").exists():
        raise Saida(4, f"capacidade {args.capacidade!r} não iniciada: use --iniciar")
    if not args.evento:
        return json.loads((base / "ultima_resposta.json").read_text(encoding="utf-8"))
    ev = _ler(args.evento)
    try:
        e, r = transicao(carregar(raiz, args.capacidade), ev)
    except ForaDeLugar as err:
        raise Saida(3, f"evento fora de lugar, nada foi gravado: {err}")
    if ev.tipo == "limpeza_feita":
        _conferir_limpeza(raiz, base, args.capacidade, ev.removidos)
    return _gravar_rodada(raiz, e, ev, r)


def principal(argv, raiz="."):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--capacidade")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--iniciar")
    g.add_argument("--evento")
    p.add_argument("--raiz", default=raiz)
    try:
        args = p.parse_args(argv)
    except SystemExit:
        print(USO, file=sys.stderr)
        return 2
    try:
        r = executar(args, args.raiz)
    except Saida as s:
        print(s, file=sys.stderr)
        return s.codigo
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
