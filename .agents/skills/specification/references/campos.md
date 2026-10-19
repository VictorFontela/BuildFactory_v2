# Como marcar os 4 campos

Cada campo diz se o passo toca uma camada. O Orchestrator liga um ator por campo:

| Campo | O passo toca… | Ator |
|---|---|---|
| `interface` | o que o usuário vê ou usa na tela | Frontend |
| `servidor` | rota, API, query, banco, job agendado, infraestrutura ou outro código do servidor | Backend |
| `agente_llm` | prompt, tool ou a forma de chamar o LLM | AI |
| `seguranca` | login, permissão, dado pessoal, ou um LLM ganhando acesso a dados | Security |

## A regra

| Valor | Quando | Trecho |
|---|---|---|
| `true` | o pedido diz, com outras palavras ou não, que o passo mexe nessa camada | obrigatório |
| `"incerto"` | o pedido não diz, mas entregar o que ele pede pode precisar mexer nessa camada | obrigatório: as palavras que levantam a dúvida |
| `false` | o pedido claramente não toca essa camada | vazio |

**Na dúvida entre `false` e `incerto`, marque `incerto`.** Um `false` errado esconde trabalho: o builder não é chamado e ninguém percebe. Um `incerto` errado custa uma decisão do Orchestrator, que lê o trecho e desliga.

**Trecho é cópia exata** de palavras do pedido, nunca uma paráfrase. Se você não consegue apontar as palavras, o valor não é `true`.

## Perguntas para cada campo

- **interface:** o usuário vai ver ou usar algo diferente na tela? Um botão, um texto, uma lista, um filtro, uma resposta que aparece no chat.
- **servidor:** algum dado precisa ser buscado, gravado, filtrado, calculado ou apagado? Algo roda sozinho, por agenda? Muda versão, contêiner ou deploy? Uma tela que mostra dado novo quase sempre precisa de um endpoint que entregue esse dado.
- **agente_llm:** o assistente passa a dizer, decidir ou fazer algo diferente? Muda o prompt, ganha uma tool, muda o formato da resposta dele?
- **seguranca:** envolve login, sessão ou permissão? Toca dado pessoal (nome, e-mail, CPF, log com identificação)? Um LLM passa a ler dados que antes não lia?

## Exemplos

| Pedido | interface | servidor | agente_llm | seguranca |
|---|---|---|---|---|
| GET /vendas: filtrar por período | false | true · "GET /vendas" | false | false |
| Tela de relatório de vendas por loja, com gráfico | true · "Tela de relatório" | incerto · "relatório de vendas por loja" | false | false |
| Prompt do agente de vendas: responder em tabela | false | false | true · "Prompt do agente" | false |
| Corrigir o texto do botão na tela de login | true · "texto do botão" | false | false | false |
| Login com SSO corporativo | true · "Login" | true · "SSO corporativo" | false | true · "Login com SSO" |
| Mascarar CPF nos logs | false | true · "nos logs" | false | true · "Mascarar CPF" |
| Nova tool do agente: consultar estoque | false | incerto · "consultar estoque" | true · "Nova tool do agente" | incerto · "consultar estoque" |
| Atualizar o Postgres no staging | false | true · "Atualizar o Postgres" | false | false |
| Atualizar o README com instruções de setup | false | false | false | false |
| Resposta do agente em streaming no chat do PDV | true · "no chat do PDV" | incerto · "em streaming" | true · "Resposta do agente" | false |

Repare:
- **"Tela de relatório":** o pedido não fala de endpoint, mas o relatório precisa de dados que hoje a tela não tem. Por isso `servidor` fica `incerto`, e não `false`.
- **"Nova tool do agente":** uma tool que consulta estoque lê dados, então `seguranca` fica `incerto` com o trecho que levanta a dúvida.
- **"Atualizar o README":** muda só documentação. Os 4 campos ficam `false`, nenhum builder atua, e Tests, Reviewer e QA atuam do mesmo jeito.
