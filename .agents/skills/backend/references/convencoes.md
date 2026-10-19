# Convenções do repositório

Cada repositório tem as suas. Antes de escrever, descubra-as nesta ordem e siga a primeira que responder:

1. `.agents/convencoes/backend.md`, se existir: as regras que o time escreveu para o servidor.
2. `AGENTS.md` (ou `CLAUDE.md`) na raiz: ambiente, como rodar testes, regras que valem sempre.
3. O código vizinho: o módulo mais parecido com o que você vai criar. Copie a forma dele: nomes, como trata erro, como organiza arquivos, como acessa o banco.

Na falta de tudo isso:
- funções pequenas, com nomes que dizem o que fazem;
- erro esperado vira exceção com nome próprio, como a spec define; não engula exceção com `except Exception: pass`;
- nenhuma dependência nova sem que a spec peça; se precisar, termine com `duvida_contrato`.
