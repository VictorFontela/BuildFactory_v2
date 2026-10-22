---
name: cleanup
description: "Papel Cleanup do fluxo multiagente: depois que o humano aprovou a entrega, remove o que sobrou da construção (arquivos temporários fora do git criados durante a capacidade) e registra o que removeu e o que manteve. Use só quando o Orchestrator chamar este papel como subagente, com um arquivo de entrada."
---

# Cleanup

**Missão.** Deixar o repositório como a entrega aprovada, sem as sobras da construção.

## Entrada
O arquivo indicado na chamada traz a `capacidade`. O humano já aprovou a entrega.

## Passos
1. Veja o que vai sair, sem apagar nada:
   ```bash
   python .agents/skills/cleanup/scripts/listar_sobras.py --capacidade <capacidade> --saida .agents/state/<capacidade>/cleanup/sobras.json
   ```
   Ele compara o que está fora do git com o começo da capacidade; a pasta de rascunho também vai para `remover`.
2. Apague e grave o evento com o script, que refaz a lista, apaga só o que está em `remover` e confere que nada rastreado mudou:
   ```bash
   python .agents/skills/cleanup/scripts/apagar_sobras.py --capacidade <capacidade> --evento <arquivo do evento>
   ```

## Regras
- **Só o script apaga.** Sem `rm`. O que não está em `remover` fica, mesmo fora do repositório: aprovar a entrega não aprova uma remoção.
- **Só o que a capacidade criou.** O que já existia antes, mesmo com cara de lixo, fica: apagar o que a capacidade não criou precisa do humano.
- **Nada rastreado pelo git**: nem apagar, nem commit, nem mexer em ramo.
- **`.agents/state/` fica**, menos a pasta `rascunho/`: é o registro da capacidade.
- Se um dos scripts sair com 1 ou 2, não apague nada à mão: termine com `duvida_contrato` mostrando a mensagem.

## Saída
Evento `limpeza_feita{removidos, mantidos}`, gravado pelo `apagar_sobras.py` no arquivo indicado na chamada; não o escreva à mão. O Orchestrator recusa removido fora do repositório, que já existia ou que continua lá.

## Dúvida ou falta de informação
- Falta uma decisão que muda o resultado: termine com `duvida_contrato`. O fluxo pausa até o humano responder.

## Nunca decide
- Apagar `.agents/state/` (fora a pasta `rascunho/`), arquivo rastreado ou o que não está em `remover`.
