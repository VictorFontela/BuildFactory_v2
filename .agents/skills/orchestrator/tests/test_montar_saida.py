"""montar_saida.py: campos da spec viram a ativação; incerto precisa de decisão; ator ativo precisa de trecho."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from montar_saida import CampoInvalido, montar  # noqa: E402

DESLIGADO = {"valor": False, "trecho": "", "decisao": None}


def campos(**kw):
    base = {"interface": DESLIGADO, "servidor": DESLIGADO, "agente_llm": DESLIGADO, "seguranca": DESLIGADO}
    return {**base, **kw}


def test_true_liga_o_ator_com_o_trecho():
    s = montar(campos(servidor={"valor": True, "trecho": "rota de export", "decisao": None}))
    assert s["builders"]["Backend"] == {"ativo": True, "trecho": "rota de export"}
    assert not s["builders"]["Frontend"]["ativo"] and not s["security"]["ativo"] and not s["builders_em_paralelo"]


def test_incerto_segue_a_decisao():
    s = montar(campos(interface={"valor": "incerto", "trecho": "tela", "decisao": True},
                      servidor={"valor": "incerto", "trecho": "dados", "decisao": False}))
    assert s["builders"]["Frontend"]["ativo"] and not s["builders"]["Backend"]["ativo"]


def test_incerto_sem_decisao_falha():
    with pytest.raises(CampoInvalido):
        montar(campos(seguranca={"valor": "incerto", "trecho": "login", "decisao": None}))


def test_valor_fora_do_contrato_falha():
    with pytest.raises(CampoInvalido):
        montar(campos(agente_llm={"valor": "sim", "trecho": "x", "decisao": None}))


def test_ativo_sem_trecho_falha():
    with pytest.raises(ValidationError):
        montar(campos(interface={"valor": True, "trecho": "", "decisao": None}))


def test_dois_builders_rodam_em_paralelo():
    s = montar(campos(interface={"valor": True, "trecho": "tela", "decisao": None},
                      agente_llm={"valor": True, "trecho": "prompt", "decisao": None}))
    assert s["builders_em_paralelo"]


def test_linha_de_comando(tmp_path):
    arq = tmp_path / "campos.json"
    arq.write_text(json.dumps(campos(seguranca={"valor": True, "trecho": "dado pessoal", "decisao": None})))
    r = subprocess.run([sys.executable, str(SCRIPTS / "montar_saida.py"), "--campos", str(arq)], capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout)["security"] == {"ativo": True, "trecho": "dado pessoal"}
