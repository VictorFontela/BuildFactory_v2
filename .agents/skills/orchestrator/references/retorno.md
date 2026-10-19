# Retorno de uma reprovação

## Evento que chega
```json
{"tipo": "reprovacao", "passo": 1, "reprovou": "QA", "motivo": "o total por loja no gráfico não bate com o banco: a soma do endpoint inclui vendas canceladas",
 "arquivos": ["web/relatorio/Grafico.tsx", "api/relatorio/agregacao.py"],
 "destino": ["Backend"], "porque": "a soma errada vem do endpoint; o gráfico só exibe o total recebido"}
```

## O que validar
1. Formato (destino não vazio, sem repetir, só builders ou Tests; `porque` preenchido): `.agents/shared/validar.py`.
2. Contexto (destino só com builders ativos neste passo, ou Tests): `proximo_estado.py`. Se falhar, devolva para quem reprovou corrigir; não conta volta.

## Contador
- `t` começa em 0 em cada passo e é único: soma voltas do Reviewer, do QA e do Security.
- Cada retorno válido: `t += 1` e o trabalho volta só para quem está no `destino`: o builder que causou o defeito, ou Tests quando o teste está errado.
- Com `t = 2`, a próxima reprovação não volta: vai para o estouro (`references/estouro.md`).

## Por que quem reprovou indica
Na 3a, com 8 reprovações: indicar pelo revisor deu 0 builder refazendo à toa; cruzar arquivos com dono deu 0,25 (erra quando a reprovação cita arquivos de dois builders); devolver para todos deu 0,875.
