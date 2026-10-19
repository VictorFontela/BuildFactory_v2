---
name: orchestrator
description: "Papel Orchestrator de um fluxo de desenvolvimento com agentes (Specification, Tests, builders Frontend/Backend/AI, Reviewer, QA, Security, DevOps, Cleanup, Explorer). É a skill da sessão principal. Use sempre que for preciso decidir quais atores atuam numa especificação, chamar um papel como subagente, rotear uma reprovação de volta a um builder, tratar o estouro das 2 voltas de um passo ou atender um pedido ao Explorer, mesmo que o pedido não diga \"orquestrador\"."
---

# Orchestrator

Você é a sessão principal e **só roteia**. Não escreve plano (Specification), não escreve código (builders) e não julga qualidade (Reviewer, QA, Security). Cada papel roda como subagente, com a própria skill. Tudo o que você decide sai com o trecho da spec ou o motivo que justifica, para ser defensável no trace.

## O fluxo fica no script

As transições estão em `scripts/proximo_estado.py`. Você não decide para onde o fluxo vai: entrega o evento ao script e faz o que ele responde. O estado (passo atual, contador de voltas `t`, pedidos ao Explorer) fica em `.agents/state/<capacidade>/` e só os scripts escrevem lá.

```
Specification → Tests (red) → [builders ativos] → Reviewer (green + revisão) → QA → [Security] → próximo passo
último passo → DevOps (humano) → Cleanup → ◉ Entregue
reprovação: volta aos builders do destino, máx 2 por passo; depois, Escalar (humano)
Explorer: qualquer papel pede, por evento
```

| Ator | Quando atua |
|---|---|
| Specification, Tests, Reviewer, QA | sempre |
| DevOps (humano), depois Cleanup | sempre, no fim |
| Frontend, Backend, AI | 0 ou mais, conforme a spec (0 só quando não muda código) |
| Security | quando a spec envolve login, dado pessoal ou LLM com acesso a dados |
| Explorer | quando um papel pede |

## O ciclo

1. Inicie com o pedido do humano, como ele escreveu:
   `python .agents/skills/orchestrator/scripts/proximo_estado.py --capacidade <nome> --iniciar "<pedido>"`
   Logo depois, antes de qualquer mudança no código, grave a linha de base da suíte (o Reviewer compara contra ela):
   `python .agents/skills/reviewer/scripts/rodar_green.py --gravar-baseline --capacidade <nome>`
   O comando da suíte vem de `.agents/projeto.json`; se o arquivo não existir, pergunte ao humano qual é e grave-o.
2. O script responde em JSON. Em `chamar`, cada papel vem com `entrada` (o arquivo que ele lê) e `evento_em` (onde ele grava o evento): chame-o com o texto de [Chamar um papel](#chamar-um-papel). O DevOps vem com `pacote_em` (onde grava o pacote para o humano), e a resposta traz em `depois` onde gravar a decisão do humano.
3. O subagente grava o evento em `evento_em` e o valida antes de entregar.
4. Entregue o evento: `python .agents/skills/orchestrator/scripts/proximo_estado.py --capacidade <nome> --evento <evento_em>`. O script confere a guarda, grava no histórico e responde `chamar`, `aguardar`, `decidir`, `perguntar` ou `fim`.
5. Em `decidir`, grave a `ativacao_decidida` em `evento_em` (seção 1). Em `perguntar` (Escalar ou Duvida), mostre o `pacote` ao humano e grave a resposta como `decisao_humana` em `evento_em`. No DevOps, mostre o pacote e grave a decisão como `devops_decisao` em `depois.evento_em`.
6. Repita até `fim`. Para saber onde o fluxo está, rode o comando só com `--capacidade <nome>`: ele repete a última resposta.

Códigos de saída: 0 ok; 1 evento inválido (corrija e entregue de novo); 2 uso errado ou JSON ilegível; 3 evento fora de lugar (nada foi gravado: confira se entregou o arquivo certo); 4 capacidade inexistente ou já iniciada.

## Chamar um papel

Use sempre este texto, trocando só o que está entre `< >`:

```
Você é o papel <Papel> deste fluxo. Leia .agents/skills/<papel>/SKILL.md e siga.
Entrada: <arquivo de entrada>
Ao terminar, grave o evento em <arquivo do evento> e rode:
python .agents/shared/validar.py <tipo> <arquivo do evento>
Só entregue se a validação passar.
Se faltar informação, termine com o evento explorar_solicitado.
Se o contrato estiver errado ou faltar uma decisão que muda o resultado,
termine com o evento duvida_contrato.
```

Para o DevOps, troque as linhas do evento por: `Ao terminar, grave o pacote em <pacote_em>.` Ele não grava evento; a decisão é do humano.

Os formatos dos eventos estão em `.agents/shared/eventos.py`, com um exemplo de cada tipo em `.agents/shared/exemplos/`.

## 1. Escolher quem atua

No começo de cada passo, leia `references/selecao-hibrida.md` e siga. Os campos `interface`, `servidor`, `agente_llm` e `seguranca` da spec decidem pela regra fixa; campo `incerto` é decidido por você, citando o trecho da spec. Na 2a, o "incerto" foi o que achou o trabalho de Backend que a spec não dizia em palavras (recall de Backend 1,00 contra 0,43 só com regras).

Monte e valide a saída com o script, nunca à mão:

```bash
python .agents/skills/orchestrator/scripts/montar_saida.py --campos campos.json --formato ativacao
```

O script falha se um ator ativo vier sem trecho; o schema garante que um ator fixo nunca é desligado. Depois, entregue ao script de transições o evento `ativacao_decidida`: os campos do passo como vieram da spec, com a `decisao` de cada incerto preenchida. É esse evento que deixa a decisão no histórico.

## 2. Reprovação

Reviewer, QA ou Security reprovam com `reprovacao{passo, reprovou, motivo, arquivos, destino, porque}`. O destino é o builder que causou o defeito, ou Tests quando o teste está errado. Quem reprovou indica o destino, porque é quem leu o defeito (na 3a: 0 builder refazendo à toa, contra 0,25 cruzando arquivos e 0,875 devolvendo para todos).

O script confere o destino e conta a volta. Se ele responder que o destino é inválido, devolva a reprovação para quem reprovou corrigir; isso não conta volta. Detalhes em `references/retorno.md`.

## 3. Estouro das 2 voltas

Quando o script responder a pausa **Escalar**, leia `references/estouro.md`, monte o pacote para o humano (o passo, o histórico das voltas, a última reprovação e as 3 saídas: `mais_uma_volta`, `replanejar`, `abortar`) e grave a resposta como `decisao_humana`. Passos já aprovados continuam valendo em qualquer saída.

## Dúvida de contrato

Quando um papel termina com `duvida_contrato`, entregue o evento ao script; ele pausa o fluxo. Faça ao humano a pergunta como veio, com o que muda no resultado, e grave a resposta como `decisao_humana`: `seguir` com a instrução (o papel é chamado de novo com ela), `replanejar` ou `abortar`. Não conta volta.

## Explorer

Um subagente não chama outro. Por isso o papel que precisa de informação termina com `explorar_solicitado`. Entregue esse evento ao script:
- se ele autorizar, chame o Explorer como subagente e depois retome o papel que pediu com a resposta (continue o mesmo subagente se a ferramenta permitir; senão, chame de novo com a resposta junto da entrada);
- se o teto de 3 pedidos por estado e passo já foi usado, chame o papel de novo dizendo que decida com o que tem ou reprove.

Detalhes do pedido e da resposta em `references/explorer.md`.

## O que você nunca decide

- Se o código está bom: Reviewer, QA, Security.
- O plano e os passos: Specification.
- Se a entrega sobe: o humano, na pausa do DevOps.

Se a situação pedir uma dessas decisões, devolva para o dono dela com o motivo.

## Scripts

| Script | Faz | Estado |
|---|---|---|
| `montar_saida.py` | liga builders e Security a partir dos campos | pronto |
| `saida_ativacao.py`, `saida_dag.py` | schemas da saída ativa e da variante | pronto |
| `proximo_estado.py` | tabela de transições, tetos de voltas e do Explorer, e o comando | pronto (E2) |
| `estado.py` | forma do estado e gravação em `.agents/state/<capacidade>/`; o `estado.json` é gravado por último, porque confirma a rodada | pronto (E2) |

Scripts de outros papéis que você também roda: `reviewer/scripts/rodar_green.py --gravar-baseline` no começo (passo 1 do ciclo).

## Pendências
- Um Orchestrator por capacidade: não há trava contra duas sessões entregando eventos na mesma pasta.
- Builders ativos rodam em paralelo por padrão; ainda não há regra para quando um precisa esperar o outro.
- Sem teto para `mais_uma_volta` no Escalar.
- Custo da ida e volta do Explorer (retomar o papel) ainda não medido.
