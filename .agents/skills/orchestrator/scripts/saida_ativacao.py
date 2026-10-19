"""Saída do orquestrador no formato ativação: o fluxo fica fixo no código; a saída só liga e desliga o que varia."""
from pydantic import BaseModel, ConfigDict, model_validator


class Ativacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ativo: bool
    trecho: str = ""

    @model_validator(mode="after")
    def ativo_tem_trecho(self):
        if self.ativo and not self.trecho:
            raise ValueError("ator ativo sem trecho da spec")
        return self


class Builders(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Frontend: Ativacao
    Backend: Ativacao
    AI: Ativacao


class Saida(BaseModel):
    model_config = ConfigDict(extra="forbid")
    builders: Builders
    security: Ativacao
    builders_em_paralelo: bool
