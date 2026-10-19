# Critérios de um passo

Cada critério é uma frase que um teste confere: dado isto, acontece aquilo. O Tests escreve pelo menos um teste por critério; o Reviewer e o QA aprovam contra eles.

## Como escrever
1. **Um comportamento por critério**, com o nome que o código vai usar quando o pedido der: a função, a rota, o campo, o botão.
2. **Tudo o que o pedido pede vira critério.** Releia o pedido e confira que nenhuma exigência ficou de fora.
3. **Os limites que o pedido nomeia viram critério próprio**: "mais de 5", "exatamente 90 dias", "vazio", "só do próprio usuário". É neles que o defeito costuma morar.
4. **O caso de erro que o pedido nomeia** ("id que não existe", "status inválido") vira critério com o que acontece.
5. **Não invente.** O que o pedido não diz não vira critério: ordem, formato, mensagem ou regra que você acharia boa. Se faltar algo que muda o resultado, termine com `duvida_contrato`.
6. **Verificável**: "rápido" ou "bonito" não se testa; "responde 404" se testa.

## Exemplo
Pedido: "Apagar tarefas concluídas há mais de 90 dias; pendentes ficam. Quero saber quais foram apagadas."

```json
"criterios": [
  "apagar_antigas(repo, hoje) apaga as tarefas concluídas há mais de 90 dias antes de hoje",
  "tarefa concluída há exatamente 90 dias não é apagada",
  "tarefas pendentes nunca são apagadas, mesmo antigas",
  "devolve os ids das tarefas apagadas"
]
```
Não entra "devolve em ordem crescente": o pedido não diz. Se a ordem importar para quem pediu, é `duvida_contrato`.
