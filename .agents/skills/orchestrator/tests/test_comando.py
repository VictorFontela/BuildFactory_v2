"""E2b: o comando proximo_estado.py, rodado de ponta a ponta numa pasta temporária."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from test_transicoes import EX, TODO, ev, resumo  # noqa: E402

SCRIPT = AQUI.parent / "scripts" / "proximo_estado.py"
CAP = "todo-concluir"
PEDIDO = EX["capacidade_criada"]["pedido"]


def cmd(raiz, *args, capacidade=CAP):
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--raiz", str(raiz), "--capacidade", capacidade, *args],
                       capture_output=True, text=True)
    return r.returncode, (json.loads(r.stdout) if r.returncode == 0 else r.stderr)


def emissor(evento):
    return {"spec_pronta": "Specification", "testes_red": "Tests", "explorer_resposta": "Explorer",
            "limpeza_feita": "Cleanup", "build_pronto": evento.get("builder"),
            "aprovado": evento.get("papel"), "reprovacao": evento.get("reprovou"),
            "explorar_solicitado": evento.get("quem_chamou"), "duvida_contrato": evento.get("quem")}.get(evento["tipo"])


class Sessao:
    """Faz o papel do Orchestrator: grava cada evento onde o script mandou e o entrega."""

    def __init__(self, raiz):
        self.raiz, self.onde, self.ultima = Path(raiz), {}, None

    def lembrar(self, r):
        self.ultima = r
        if r["acao"] == "chamar":
            for p in r["papeis"]:
                assert (self.raiz / p["entrada"]).is_file()
                self.onde[p["papel"]] = p.get("evento_em") or p["pacote_em"]
            if "depois" in r:
                self.onde["_pausa"] = r["depois"]["evento_em"]
        elif r["acao"] in ("decidir", "perguntar"):
            self.onde["_pausa"] = r["evento_em"]

    def iniciar(self, pedido=PEDIDO, fora_do_git=()):
        cod, r = cmd(self.raiz, "--iniciar", pedido)
        assert cod == 0, r
        base = self.raiz / ".agents" / "state" / CAP / "baseline-suite.json"
        base.write_text(json.dumps({"commit": "abc1234", "total": 0, "falhando": [], "fora_do_git": list(fora_do_git)}))
        self.lembrar(r)
        return r

    def entregar(self, evento):
        quem = emissor(evento)
        destino = self.raiz / (self.onde[quem] if quem in self.onde else self.onde["_pausa"])
        destino.write_text(json.dumps(evento, ensure_ascii=False))
        cod, r = cmd(self.raiz, "--evento", str(destino))
        if cod == 0:
            self.lembrar(r)
        return cod, r


def estado_bytes(raiz):
    base = Path(raiz) / ".agents" / "state" / CAP
    return hashlib.sha256((base / "estado.json").read_bytes()).hexdigest(), len(list((base / "eventos").iterdir()))


def test_todo_de_ponta_a_ponta_pelo_comando(tmp_path):
    s = Sessao(tmp_path)
    assert resumo(s.iniciar()) == TODO[0][1][0]
    for evento, (esperado, _, _) in TODO[1:]:
        cod, r = s.entregar(evento)
        assert cod == 0, r
        assert resumo(r) == esperado
    base = tmp_path / ".agents" / "state" / CAP
    eventos = sorted(p.name for p in (base / "eventos").iterdir())
    assert len(eventos) == 19
    assert eventos[0].endswith("capacidade_criada.json") and eventos[-1].endswith("limpeza_feita.json")
    assert json.loads((base / "estado.json").read_text())["fase"] == "Entregue"
    assert cmd(tmp_path) == (0, s.ultima)
    numeros = [int(n[:4]) for n in eventos + [p.name for p in (base / "entradas").iterdir()]]
    assert len(numeros) == len(set(numeros))


def test_devops_monta_pacote_e_o_humano_decide(tmp_path):
    s = Sessao(tmp_path)
    s.iniciar()
    for evento, _ in TODO[1:16]:
        s.entregar(evento)
    cod, r = s.entregar(TODO[16][0])
    assert resumo(r) == "chamar DevOps"
    devops = r["papeis"][0]
    assert devops["pacote_em"].endswith("-devops-pacote.md") and "evento_em" not in devops
    assert r["depois"]["tipo_esperado"] == "devops_decisao" and r["depois"]["evento_em"].endswith("-humano.json")


def test_fora_de_lugar_e_invalido_nao_gravam_nada(tmp_path):
    s = Sessao(tmp_path)
    s.iniciar()
    for evento, _ in TODO[1:5]:
        s.entregar(evento)
    antes = estado_bytes(tmp_path)
    cod, msg = s.entregar(ev("aprovado", papel="QA"))
    assert cod == 3 and "fora de lugar" in msg and estado_bytes(tmp_path) == antes
    cod, msg = s.entregar(ev("aprovado", papel="Reviewer", evidencia="ok"))
    assert cod == 1 and "evidencia" in msg and estado_bytes(tmp_path) == antes
    cod, r = s.entregar(ev("aprovado", papel="Reviewer", evidencia="2 de 2 testes passam"))
    assert cod == 0 and resumo(r) == "chamar QA"


def test_codigos_de_uso(tmp_path):
    assert cmd(tmp_path, "--evento", "x.json")[0] == 4
    Sessao(tmp_path).iniciar()
    assert cmd(tmp_path, "--iniciar", PEDIDO)[0] == 4
    assert cmd(tmp_path, "--iniciar", PEDIDO, capacidade="Nome Com Espaco")[0] == 1
    assert cmd(tmp_path, "--iniciar", "oi", capacidade="outra")[0] == 1
    cerca = tmp_path / "cerca.json"
    cerca.write_text("```json\n{}\n```")
    assert cmd(tmp_path, "--evento", str(cerca))[0] == 2
    assert cmd(tmp_path, "--evento", str(tmp_path / "nao-existe.json"))[0] == 2


def test_dois_builders_recebem_entradas_e_saidas_separadas(tmp_path):
    spec = {"tipo": "spec_pronta", "passos": [{"id": 1, "descricao": "tela e API de status", "criterios": ["concluir muda o status"], "diretorios": ["api/", "web/src/tarefas/"],
            "campos": {"interface": {"valor": True, "trecho": "tela"}, "servidor": {"valor": True, "trecho": "API"},
                       "agente_llm": {"valor": False}, "seguranca": {"valor": False}}}]}
    s = Sessao(tmp_path)
    s.iniciar()
    s.entregar(spec)
    s.entregar({"tipo": "ativacao_decidida", "passo": 1, "campos": spec["passos"][0]["campos"]})
    cod, r = s.entregar(ev("testes_red"))
    assert resumo(r) == "chamar Frontend+Backend"
    caminhos = {p["evento_em"] for p in r["papeis"]} | {p["entrada"] for p in r["papeis"]}
    assert len(caminhos) == 4
    cod, r = s.entregar(ev("build_pronto", builder="Frontend", arquivos=["web/src/tarefas/Lista.tsx"]))
    assert resumo(r) == "aguardar Backend"
    cod, r = s.entregar(ev("build_pronto"))
    assert resumo(r) == "chamar Reviewer"


def ate_o_cleanup(tmp_path, fora_do_git=()):
    s = Sessao(tmp_path)
    s.iniciar(fora_do_git=fora_do_git)
    for evento, _ in TODO[1:-1]:
        cod, r = s.entregar(evento)
        assert cod == 0, r
    assert resumo(s.ultima) == "chamar Cleanup"
    return s


def test_limpeza_so_do_que_a_capacidade_criou(tmp_path):
    (tmp_path / "notas.txt").write_text("do humano")
    (tmp_path / "ja-existia").mkdir()
    s = ate_o_cleanup(tmp_path, fora_do_git=["ja-existia/"])
    antes = estado_bytes(tmp_path)
    for removidos, motivo in [(["ja-existia/"], "já existia antes"), ([f".agents/state/{CAP}/estado.json"], "registro da capacidade"),
                              (["notas.txt"], "continua lá")]:
        cod, msg = s.entregar(ev("limpeza_feita", removidos=removidos))
        assert cod == 1 and motivo in msg and estado_bytes(tmp_path) == antes, msg
    cod, msg = s.entregar(ev("limpeza_feita", removidos=["/tmp/todo-ativacao.json"]))
    assert cod == 1 and "relativo" in msg and estado_bytes(tmp_path) == antes
    cod, r = s.entregar(ev("limpeza_feita", removidos=[f".agents/state/{CAP}/rascunho/", "web/.tmp-mock-tarefas.json"]))
    assert cod == 0 and resumo(r) == "fim Entregue"


def test_limpeza_sem_linha_de_base_e_recusada(tmp_path):
    s = ate_o_cleanup(tmp_path)
    (tmp_path / ".agents" / "state" / CAP / "baseline-suite.json").unlink()
    cod, msg = s.entregar(ev("limpeza_feita"))
    assert cod == 1 and "sem linha de base" in msg
