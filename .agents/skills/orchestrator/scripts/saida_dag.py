"""Saída do orquestrador no formato DAG: nós e dependências (variante para comparar na Etapa 5)."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator

Ator = Literal["Specification", "Tests", "Frontend", "Backend", "AI", "Reviewer", "QA", "Security", "DevOps", "Cleanup"]
FIXOS = {"Specification", "Tests", "Reviewer", "QA", "DevOps", "Cleanup"}


class No(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ator: Ator
    depende_de: list[Ator]


class Saida(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nos: list[No]

    @model_validator(mode="after")
    def grafo_valido(self):
        atores = [n.ator for n in self.nos]
        if len(atores) != len(set(atores)):
            raise ValueError("ator repetido")
        if FIXOS - set(atores):
            raise ValueError(f"fixo ausente: {sorted(FIXOS - set(atores))}")
        deps = {n.ator: set(n.depende_de) for n in self.nos}
        for a, d in deps.items():
            if d - set(atores):
                raise ValueError(f"{a} depende de ator fora do grafo: {sorted(d - set(atores))}")
        visitados, pilha = set(), set()

        def visita(a):
            if a in pilha:
                raise ValueError("ciclo no grafo")
            if a in visitados:
                return
            pilha.add(a)
            for d in deps[a]:
                visita(d)
            pilha.discard(a)
            visitados.add(a)

        for a in deps:
            visita(a)
        return self
