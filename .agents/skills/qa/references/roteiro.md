# Como montar o cenário

Os testes do Tests conferem cada critério com o mínimo de dados. O defeito que passa por eles mora no que o mínimo não alcança. Para cada critério, monte:

1. **Mais volume.** Dados suficientes para o comportamento aparecer de verdade: mais de uma página, várias entidades, listas com dezenas de itens.
2. **Os limites, dos dois lados.** "Mais de 90 dias": teste 89, 90 e 91. "5 tentativas": teste 4, 5 e 6. "Vazio": teste vazio e um item.
3. **Combinações.** Dois critérios ao mesmo tempo: filtro com paginação, falha de um usuário seguida de falha de outro, item com vírgula e aspas no mesmo campo.
4. **Sequências.** O que acontece depois: falha, falha, sucesso, falha; criar, concluir, listar; exportar e ler de volta.
5. **Entidades separadas.** O que é de um não pode afetar o outro: outro usuário, outra tarefa, outra loja.
6. **O caminho de quem usa.** Comece pelo que o pedido descreve ("quero ver só as concluídas") e vá até o resultado que a pessoa veria.

## Como rodar
- Função ou módulo: um script que importa a interface pública e imprime entrada, esperado e obtido de cada verificação.
- API: suba o servidor local (como o `AGENTS.md` ou o README dizem) e chame as rotas; pare o servidor no fim.
- Tela: suba o front local e percorra a tela com o navegador automatizado do ambiente (Playwright, se houver).

Faça cada verificação imprimir `OK` ou `FALHOU: entrada, esperado, obtido`. A saída vira a evidência.

## Exemplo
Critérios: "status pendentes traz só as não concluídas" e "o filtro é aplicado antes da paginação, 20 por página".
- 45 tarefas, uma em cada três concluída → 30 pendentes.
- `status=pendentes`: página 1 tem 20, página 2 tem 10, página 3 vem vazia; nenhuma concluída nas três.
- Mesmo com `status=concluidas`: 15 na página 1, página 2 vazia.
