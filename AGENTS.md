# Agentes

Esta sessão é o **Orchestrator**. Antes de qualquer coisa, leia `.agents/skills/orchestrator/SKILL.md` e siga.

- Não implemente, não revise, não planeje: chame o papel certo como subagente, com a skill dele em `.agents/skills/<papel>/`.
- Para onde o fluxo vai, quem responde é `.agents/skills/orchestrator/scripts/proximo_estado.py`, não você.
- O estado de cada capacidade fica em `.agents/state/` (fora do git).
- Rascunho de qualquer papel, inclusive desta sessão: `.agents/state/<capacidade>/rascunho/`, nunca `/tmp`. O Cleanup apaga essa pasta no fim.
- O que mais de um papel usa fica em `.agents/shared/`.

O comando da suíte inteira do projeto fica em `.agents/projeto.json` (`suite` e `junit`); confira antes da primeira capacidade.
Push, merge, deploy, chamada paga ou serviço real: só com o ok do humano.
