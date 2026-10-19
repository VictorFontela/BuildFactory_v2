# LLM com tool, consulta ou acesso a dados

O modelo faz o que o texto manda, inclusive texto que veio do usuário ou de um documento. Trate todo argumento que o modelo passa a uma tool como entrada de um desconhecido.

Reprove quando o diff:
1. **A tool não confere o dono**: o modelo pode pedir o dado de qualquer cliente; a tool precisa saber em nome de quem roda (o usuário da sessão, passado pelo código, não pelo modelo) e filtrar por ele.
2. **O argumento da tool vai direto para consulta, arquivo ou comando** sem validação de tipo e limite (Pydantic, enum, tamanho).
3. **A tool devolve campos sensíveis** que o modelo não precisa (hash de senha, documento completo, token): o que a tool devolve pode sair na resposta do modelo.
4. **Ação que muda dado ou custa dinheiro** (apagar, pagar, enviar) sem a confirmação que a spec pede.
5. **Prompt com segredo ou dado de outro cliente** dentro do texto de sistema ou do contexto.
6. **Saída do modelo usada como código, consulta ou HTML** sem tratar como texto não confiável.

Como provar: chame a tool como o modelo chamaria, com argumentos de outro dono ou fora do limite, e mostre o que volta.
