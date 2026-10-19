# Langfuse (quando o projeto usa)

Siga o padrão que o projeto já tem: procure no código vizinho como ele cria trace, span e versiona prompt, e faça igual. Se não houver padrão, termine com `explorar_solicitado` ou `duvida_contrato`; não invente um.

- **Prompt**: se o projeto guarda prompts no Langfuse, a versão nova do prompt é uma versão nova no Langfuse, com o mesmo nome; o código referencia por nome e rótulo, como os vizinhos. Criar ou publicar versão no Langfuse de verdade é ação em serviço real: precisa do ok do humano. No passo, deixe o texto do prompt no arquivo do repositório e diga no `resumo` que falta publicar.
- **Trace**: chamada nova ao modelo entra no trace com o nome do nó ou da tool, como as outras. Metadados sem dado de cliente.
- **Testes**: nenhum teste fala com o Langfuse de verdade. Use o mesmo desligamento ou falso que os testes do projeto já usam.
