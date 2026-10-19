# Convenções da tela

Cada repositório tem as suas. Antes de escrever, descubra-as nesta ordem e siga a primeira que responder:

1. `.agents/convencoes/frontend.md`, se existir: as regras que o time escreveu para a tela.
2. `AGENTS.md` (ou `CLAUDE.md`) na raiz e o `package.json`: framework, como rodar testes, lint.
3. O código vizinho: o componente mais parecido com o que você vai criar. Copie a forma dele: nomes, onde fica o estado, como chama a API, como estiliza.

Na falta de tudo isso:
- funções e componentes pequenos, com nomes que dizem o que mostram;
- a lógica da tela (filtrar, montar o que aparece, mudar o estado) separada do que desenha, para dar para testar sem navegador;
- texto do usuário sempre escapado, nunca concatenado cru em HTML;
- nenhuma dependência nova sem que a spec peça; se precisar, termine com `duvida_contrato`.
