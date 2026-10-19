# Convenções do agente

Cada repositório tem as suas. Antes de escrever, descubra-as nesta ordem e siga a primeira que responder:

1. `.agents/convencoes/ai.md`, se existir: as regras que o time escreveu para o agente.
2. `AGENTS.md` (ou `CLAUDE.md`) na raiz: framework do agente (LangGraph, SDK do provedor), como rodar testes, o que custa dinheiro.
3. O código vizinho: a tool, o nó ou o prompt mais parecido com o que você vai criar. Copie a forma dele.

Na falta de tudo isso:
- **Cliente injetado.** A função recebe o cliente do LLM por parâmetro; não cria cliente de verdade dentro dela. Nos testes, o cliente é um falso que devolve texto fixo e guarda o que recebeu.
- **Prompt em arquivo versionado** (`<nome>_v1.txt`, ou o padrão do projeto), lido pelo código; não espalhado em strings no meio da lógica. Mudou o sentido do prompt, nova versão.
- **Argumentos de tool validados** com o modelo do projeto (Pydantic, se for Python) antes de tocar em qualquer dado.
- **Erro vira resultado, não exceção solta**: a tool devolve `{"ok": false, "erro": "..."}` (ou o padrão do projeto) para o modelo poder reagir; o mesmo para falha do cliente, quando a spec define a resposta.
- **Não chame o modelo quando não precisa**: entrada vazia ou sem nada a fazer responde sem a chamada.
- **Dado de cliente** não vai para log, print nem trace sem a spec pedir.
