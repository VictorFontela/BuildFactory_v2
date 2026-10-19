"""Estado de uma capacidade: onde o fluxo está, o passo, as voltas e os pedidos ao Explorer.

Só os scripts do Orchestrator escrevem aqui. Cada capacidade tem uma pasta em
.agents/state/<capacidade>/:

    estado.json                 onde o fluxo está
    ultima_resposta.json        a última resposta do script (o "onde estou")
    eventos/NNNN-<tipo>.json    cada evento aceito, só acrescenta: é o histórico
    entradas/NNNN-<papel>.json  o que cada papel recebeu
    saidas/                     onde papéis e humano gravam o evento antes de entregá-lo
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Fase = Literal["Specification", "Ativacao", "Tests", "Builders", "Reviewer", "QA", "Security",
               "DevOps", "Cleanup", "Escalar", "Duvida", "Explorer", "Entregue", "Falhou"]


class Retomar(BaseModel):
    """Para onde voltar depois de um pedido ao Explorer ou de uma dúvida de contrato."""
    model_config = ConfigDict(extra="forbid")
    fase: Fase
    quem: str
    pendentes: list[str] = Field(default_factory=list)


class Estado(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capacidade: str
    pedido: str
    fase: Fase
    passos: list[dict] = Field(default_factory=list)
    passo: int | None = None
    t: int = 0
    ativos: dict[str, list[str]] = Field(default_factory=dict, description="passo → builders ativos")
    security: dict[str, bool] = Field(default_factory=dict, description="passo → Security ativo")
    pendentes: list[str] = Field(default_factory=list, description="builders que ainda não entregaram")
    testes: dict | None = None
    builds: dict[str, dict] = Field(default_factory=dict, description="builder → último build_pronto do passo")
    voltas: list[dict] = Field(default_factory=list, description="reprovações válidas do passo")
    destino_ultima: list[str] = Field(default_factory=list)
    explorer: dict[str, int] = Field(default_factory=dict, description="'passo:papel' → pedidos usados")
    retomar: Retomar | None = None
    replanejar_de: int | None = None
    seq: int = Field(default=0, description="último número usado em eventos/, entradas/ e saidas/")


def pasta(raiz: Path, capacidade: str) -> Path:
    return Path(raiz) / ".agents" / "state" / capacidade


def gravar_json(caminho: Path, dados) -> None:
    """Grava inteiro ou não grava: escreve num temporário e troca de uma vez."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=caminho.parent, prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, caminho)


def carregar(raiz: Path, capacidade: str) -> Estado:
    return Estado.model_validate_json((pasta(raiz, capacidade) / "estado.json").read_text(encoding="utf-8"))


def salvar(raiz: Path, e: Estado) -> None:
    gravar_json(pasta(raiz, e.capacidade) / "estado.json", e.model_dump(mode="json"))
