---
name: cleanup
description: "Papel Cleanup do fluxo multiagente: depois que o humano aprovou a entrega, remove o que sobrou da construção (arquivos temporários fora do git criados durante a capacidade) e registra o que removeu e o que manteve. Use só quando o Orchestrator chamar este papel como subagente, com um arquivo de entrada."
---

# Cleanup

**Missão.** Deixar o repositório como a entrega aprovada, sem as sobras da construção.

## Entrada
O arquivo indicado na chamada traz a `capacidade`. O humano já aprovou a entrega.

## Passos
1. Liste as sobras:
   ```bash
   python .agents/skills/cleanup/scripts/listar_sobras.py --capacidade <capacidade> --saida .agents/state/<capacidade>/cleanup/sobras.json
   ```
   O script compara o que está fora do git agora com o que estava no começo da capacidade. Ele não apaga nada.
2. Apague **só** o que está em `remover`, um caminho por vez (`rm -r -- <caminho>`).
3. Não toque no que está em `manter` nem em `avisar`. `avisar` vai para o humano, no evento.
4. Confira com `git status` que nada rastreado mudou.

## Regras
- **Só o que a capacidade criou.** O que já existia antes, mesmo com cara de lixo, fica: apagar o que a capacidade não criou precisa do humano.
- **Nada rastreado pelo git**: nem apagar, nem commit, nem mexer em ramo.
- **`.agents/state/` fica**: é o registro da capacidade.
- Se o script sair com 2 (sem linha de base ou outro erro de uso), não apague nada: termine com `duvida_contrato` mostrando a mensagem.

## Saída
Evento `limpeza_feita{removidos, mantidos}`:
- `removidos`: os caminhos que você apagou;
- `mantidos`: os de `manter` e os de `avisar`, cada um com o motivo depois de ` — ` (`"app/rascunho.py — entrou em commit com nome de rascunho: o humano decide"`).

Grave no arquivo indicado na chamada e rode `python .agents/shared/validar.py limpeza_feita <arquivo>`. Só entregue se passar.

## Dúvida ou falta de informação
- Falta uma decisão que muda o resultado: termine com `duvida_contrato`. O fluxo pausa até o humano responder.

## Nunca decide
- Apagar `.agents/state/`, arquivo rastreado ou o que não está em `remover`.
