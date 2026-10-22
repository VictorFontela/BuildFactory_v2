"""E1: cada evento tem um exemplo válido e cada regra tem um caso inválido que ela recusa."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

AQUI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AQUI))
from eventos import TIPOS, validar  # noqa: E402

EX = {t: json.loads((AQUI / "exemplos" / f"{t}.json").read_text(encoding="utf-8")) for t in TIPOS}


def muda(tipo, f):
    d = copy.deepcopy(EX[tipo])
    f(d)
    return d


def campo(d, i, nome, v):
    d["passos"][i]["campos"][nome] = v


INVALIDOS = [
    ("capacidade_criada", "nome com espaço", lambda d: d.update(capacidade="Todo Concluir")),
    ("capacidade_criada", "pedido vazio", lambda d: d.update(pedido="  ")),
    ("spec_pronta", "sem passos", lambda d: d.update(passos=[])),
    ("spec_pronta", "ids fora de ordem", lambda d: d["passos"][1].update(id=3)),
    ("spec_pronta", "passo sem critérios", lambda d: d["passos"][0].update(criterios=[])),
    ("spec_pronta", "passo sem diretórios", lambda d: d["passos"][0].update(diretorios=[])),
    ("spec_pronta", "diretório absoluto", lambda d: d["passos"][0].update(diretorios=["/etc"])),
    ("spec_pronta", "diretório com ..", lambda d: d["passos"][0].update(diretorios=["api/../segredo"])),
    ("spec_pronta", "true sem trecho", lambda d: campo(d, 0, "servidor", {"valor": True, "trecho": ""})),
    ("spec_pronta", "incerto sem trecho", lambda d: campo(d, 1, "servidor", {"valor": "incerto"})),
    ("spec_pronta", "Specification decidindo o incerto", lambda d: campo(d, 1, "servidor", {"valor": "incerto", "trecho": "filtrar", "decisao": False})),
    ("spec_pronta", "campo faltando", lambda d: d["passos"][0]["campos"].pop("seguranca")),
    ("spec_pronta", "campo a mais", lambda d: d["passos"][0].update(builders=["Backend"])),
    ("ativacao_decidida", "incerto sem decisão", lambda d: d["campos"]["servidor"].pop("decisao")),
    ("ativacao_decidida", "decisão em campo que não é incerto", lambda d: d["campos"]["interface"].update(decisao=True)),
    ("ativacao_decidida", "campo ligado sem trecho", lambda d: d["campos"]["interface"].update(trecho="")),
    ("testes_red", "sem falhas", lambda d: d.update(falhas=[])),
    ("testes_red", "commit que não é hash", lambda d: d.update(commit="ultimo")),
    ("testes_red", "sem arquivos", lambda d: d.update(arquivos=[])),
    ("testes_red", "passo 0", lambda d: d.update(passo=0)),
    ("build_pronto", "builder que não existe", lambda d: d.update(builder="Security")),
    ("build_pronto", "sem commit", lambda d: d.pop("commit")),
    ("build_pronto", "arquivo fora da raiz", lambda d: d.update(arquivos=["../outro/app.py"])),
    ("aprovado", "papel que não revisa", lambda d: d.update(papel="Tests")),
    ("aprovado", "evidência curta", lambda d: d.update(evidencia="ok")),
    ("reprovacao", "destino vazio", lambda d: d.update(destino=[])),
    ("reprovacao", "destino repetido", lambda d: d.update(destino=["Backend", "Backend"])),
    ("reprovacao", "destino que não constrói", lambda d: d.update(destino=["DevOps"])),
    ("reprovacao", "sem porquê", lambda d: d.update(porque="")),
    ("reprovacao", "builder reprovando", lambda d: d.update(reprovou="Backend")),
    ("explorar_solicitado", "escopo vazio", lambda d: d.update(escopo=[])),
    ("explorar_solicitado", "sem para quê", lambda d: d.pop("para_que")),
    ("explorar_solicitado", "humano pedindo", lambda d: d.update(quem_chamou="Humano")),
    ("explorer_resposta", "sem achados e nao_achou false", lambda d: d.update(achados=[])),
    ("explorer_resposta", "achados e nao_achou true", lambda d: d.update(nao_achou=True)),
    ("explorer_resposta", "achado sem fonte", lambda d: d["achados"][0].update(fonte="")),
    ("duvida_contrato", "sem o que muda", lambda d: d.pop("por_que_muda")),
    ("duvida_contrato", "pergunta curta", lambda d: d.update(pergunta="?")),
    ("decisao_humana", "saída que não existe", lambda d: d.update(saida="talvez")),
    ("decisao_humana", "mais uma volta sem instrução", lambda d: d.update(saida="mais_uma_volta", instrucao="")),
    ("decisao_humana", "seguir sem instrução", lambda d: d.update(instrucao=" ")),
    ("devops_decisao", "recusa sem motivo", lambda d: d.update(aprovado=False, motivo="")),
    ("limpeza_feita", "sem removidos", lambda d: d.pop("removidos")),
    ("limpeza_feita", "removido fora do repositório", lambda d: d.update(removidos=["/tmp/todo-ativacao.json"])),
    ("limpeza_feita", "removido subindo de pasta", lambda d: d.update(removidos=["../outro/x"])),
]


@pytest.mark.parametrize("tipo", TIPOS)
def test_exemplo_valido(tipo):
    assert validar(EX[tipo], tipo).tipo == tipo
    assert validar(EX[tipo]).tipo == tipo


@pytest.mark.parametrize("tipo,regra,f", INVALIDOS, ids=[f"{t}: {r}" for t, r, _ in INVALIDOS])
def test_regra_recusa(tipo, regra, f):
    with pytest.raises(ValidationError):
        validar(muda(tipo, f), tipo)


def test_todo_tipo_tem_caso_invalido():
    assert {t for t, _, _ in INVALIDOS} == set(TIPOS)


def test_tipo_trocado():
    with pytest.raises(ValueError, match="foi validado como"):
        validar(EX["build_pronto"], "aprovado")


def cli(*args):
    r = subprocess.run([sys.executable, "-I", str(AQUI / "validar.py"), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


def test_cli_codigos(tmp_path):
    assert cli("reprovacao", str(AQUI / "exemplos" / "reprovacao.json")) == (0, "ok reprovacao\n")
    ruim = tmp_path / "r.json"
    ruim.write_text(json.dumps(muda("reprovacao", lambda d: d.update(destino=[]))))
    cod, out = cli("reprovacao", str(ruim))
    assert cod == 1 and "- destino:" in out
    cerca = tmp_path / "c.json"
    cerca.write_text("```json\n{}\n```")
    assert cli("aprovado", str(cerca))[0] == 2
    quebrado = tmp_path / "q.json"
    quebrado.write_text("{\"tipo\": ")
    assert cli("aprovado", str(quebrado))[0] == 2
    assert cli("inexistente", str(ruim))[0] == 2
    assert cli("aprovado", str(tmp_path / "nao-existe.json"))[0] == 2
    assert cli("aprovado")[0] == 2
