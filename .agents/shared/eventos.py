"""Formatos dos eventos que passam entre os papéis do fluxo.

Este arquivo confere só o formato de cada evento. O que depende do estado do
fluxo (destino só com builders ativos no passo, contador de voltas, teto do
Explorer, `seguir` só depois de uma dúvida) é conferido pelo proximo_estado.py.
"""
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter, field_validator, model_validator

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Frase = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5)]
Commit = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{7,40}$")]
Passo = Annotated[int, Field(ge=1)]

Builder = Literal["Frontend", "Backend", "AI"]
Revisor = Literal["Reviewer", "QA", "Security"]
Papel = Literal["Specification", "Tests", "Frontend", "Backend", "AI", "Reviewer", "QA", "Security", "DevOps", "Cleanup", "Explorer"]


def caminho_relativo(c: str) -> str:
    c = c.strip()
    if not c or c.startswith(("/", "~")) or ".." in c.replace("\\", "/").split("/"):
        raise ValueError(f"caminho precisa ser relativo à raiz do repositório, sem '..': {c!r}")
    return c


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CapacidadeCriada(Base):
    tipo: Literal["capacidade_criada"]
    capacidade: Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]*$")]
    pedido: Frase


class Campo(Base):
    valor: bool | Literal["incerto"]
    trecho: str = ""
    decisao: None = None

    @model_validator(mode="after")
    def trecho_quando_liga(self):
        if self.valor is not False and not self.trecho.strip():
            raise ValueError("campo true ou incerto precisa do trecho da spec que justifica")
        return self


class Campos(Base):
    interface: Campo
    servidor: Campo
    agente_llm: Campo
    seguranca: Campo


class PassoSpec(Base):
    id: Passo
    descricao: Frase
    criterios: list[Frase] = Field(min_length=1, description="o que o passo entrega, cada um verificável por teste")
    diretorios: list[str] = Field(min_length=1)
    campos: Campos

    @field_validator("diretorios")
    @classmethod
    def diretorios_relativos(cls, v):
        return [caminho_relativo(c) for c in v]


class SpecPronta(Base):
    tipo: Literal["spec_pronta"]
    passos: list[PassoSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def ids_em_sequencia(self):
        ids = [p.id for p in self.passos]
        if ids != list(range(1, len(ids) + 1)):
            raise ValueError(f"ids dos passos precisam ser 1, 2, 3… em ordem; vieram {ids}")
        return self


class CampoDecidido(Base):
    valor: bool | Literal["incerto"]
    trecho: str = ""
    decisao: bool | None = None

    @model_validator(mode="after")
    def decisao_so_no_incerto(self):
        if self.valor is not False and not self.trecho.strip():
            raise ValueError("campo true ou incerto precisa do trecho da spec que justifica")
        if self.valor == "incerto" and self.decisao is None:
            raise ValueError("campo incerto precisa da decisão true ou false do Orchestrator")
        if self.valor != "incerto" and self.decisao is not None:
            raise ValueError("só campo incerto leva decisão")
        return self


class CamposDecididos(Base):
    interface: CampoDecidido
    servidor: CampoDecidido
    agente_llm: CampoDecidido
    seguranca: CampoDecidido


class AtivacaoDecidida(Base):
    tipo: Literal["ativacao_decidida"]
    passo: Passo
    campos: CamposDecididos


class TestesRed(Base):
    tipo: Literal["testes_red"]
    passo: Passo
    arquivos: list[str] = Field(min_length=1)
    comando: Texto
    falhas: list[Texto] = Field(min_length=1)
    commit: Commit

    @field_validator("arquivos")
    @classmethod
    def arquivos_relativos(cls, v):
        return [caminho_relativo(c) for c in v]


class BuildPronto(Base):
    tipo: Literal["build_pronto"]
    passo: Passo
    builder: Builder
    arquivos: list[str] = Field(min_length=1)
    resumo: Frase
    commit: Commit

    @field_validator("arquivos")
    @classmethod
    def arquivos_relativos(cls, v):
        return [caminho_relativo(c) for c in v]


class Aprovado(Base):
    tipo: Literal["aprovado"]
    passo: Passo
    papel: Revisor
    evidencia: Frase


class Reprovacao(Base):
    tipo: Literal["reprovacao"]
    passo: Passo
    reprovou: Revisor
    motivo: Frase
    arquivos: list[str] = Field(default_factory=list)
    destino: list[Builder | Literal["Tests"]] = Field(min_length=1)
    porque: Frase

    @field_validator("arquivos")
    @classmethod
    def arquivos_relativos(cls, v):
        return [caminho_relativo(c) for c in v]

    @field_validator("destino")
    @classmethod
    def sem_repetir(cls, v):
        if len(v) != len(set(v)):
            raise ValueError("destino com papel repetido")
        return v


class ExplorarSolicitado(Base):
    tipo: Literal["explorar_solicitado"]
    quem_chamou: Papel
    pergunta: Frase
    escopo: list[Texto] = Field(min_length=1, description="pastas, arquivos ou URLs onde procurar")
    para_que: Frase


class Achado(Base):
    fonte: Texto
    trecho: Texto


class ExplorerResposta(Base):
    tipo: Literal["explorer_resposta"]
    achados: list[Achado]
    nao_achou: bool

    @model_validator(mode="after")
    def coerente(self):
        if not self.achados and not self.nao_achou:
            raise ValueError("sem achados, nao_achou precisa ser true")
        if self.achados and self.nao_achou:
            raise ValueError("com achados, nao_achou precisa ser false")
        return self


class DuvidaContrato(Base):
    tipo: Literal["duvida_contrato"]
    quem: Papel
    passo: Passo | None = None
    pergunta: Frase
    por_que_muda: Frase = Field(description="o que muda no resultado conforme a resposta")


class DecisaoHumana(Base):
    tipo: Literal["decisao_humana"]
    saida: Literal["mais_uma_volta", "replanejar", "abortar", "seguir"]
    instrucao: str = Field("", description="as palavras do humano, como ele escreveu; o que ele não disse não entra")

    @model_validator(mode="after")
    def instrucao_quando_precisa(self):
        if self.saida in ("mais_uma_volta", "seguir") and not self.instrucao.strip():
            raise ValueError(f"{self.saida} precisa da instrução do humano")
        return self


class DevopsDecisao(Base):
    tipo: Literal["devops_decisao"]
    aprovado: bool
    motivo: str = Field("", description="as palavras do humano, como ele escreveu; o que ele não disse não entra")

    @model_validator(mode="after")
    def motivo_na_recusa(self):
        if not self.aprovado and not self.motivo.strip():
            raise ValueError("recusa precisa de motivo")
        return self


class LimpezaFeita(Base):
    """Gravado pelo apagar_sobras.py. O comando do Orchestrator confere os removidos contra a linha de base."""
    tipo: Literal["limpeza_feita"]
    removidos: list[Texto]
    mantidos: list[Texto]

    @field_validator("removidos")
    @classmethod
    def removidos_no_repositorio(cls, v):
        return [caminho_relativo(c) for c in v]


MODELOS = {m.model_fields["tipo"].annotation.__args__[0]: m for m in (
    CapacidadeCriada, SpecPronta, AtivacaoDecidida, TestesRed, BuildPronto, Aprovado, Reprovacao,
    ExplorarSolicitado, ExplorerResposta, DuvidaContrato, DecisaoHumana, DevopsDecisao, LimpezaFeita)}
TIPOS = tuple(MODELOS)

Evento = Annotated[Union[tuple(MODELOS.values())], Field(discriminator="tipo")]
_qualquer = TypeAdapter(Evento)


def validar(dados: dict, tipo: str | None = None):
    """Devolve o evento validado. Com `tipo`, exige que o evento seja desse tipo."""
    if tipo is not None:
        if tipo not in MODELOS:
            raise KeyError(f"tipo desconhecido: {tipo!r}; tipos: {', '.join(TIPOS)}")
        if dados.get("tipo") != tipo:
            raise ValueError(f"o arquivo diz tipo {dados.get('tipo')!r}, mas foi validado como {tipo!r}")
        return MODELOS[tipo].model_validate(dados)
    return _qualquer.validate_python(dados)
