---
name: specification
description: "Papel Specification do fluxo multiagente: transforma um pedido em passos testáveis e marca em cada passo os diretórios que ele pode alterar e os campos interface, servidor, agente_llm e seguranca, que decidem quem constrói. Use só quando o Orchestrator chamar este papel como subagente, com um arquivo de entrada."
---

# Specification

**Missão.** Transformar o pedido em passos pequenos e dizer, para cada passo, que camadas do sistema ele toca, sempre com as palavras do pedido que justificam. Quem decide quem constrói é o Orchestrator, a partir do que você marca.

## Entrada
O arquivo indicado na chamada traz `capacidade` e `pedido`, como o humano escreveu; ou um pedido de `replanejar_de` um passo, com o histórico das voltas e a instrução do humano.

## Passos
1. Leia o pedido inteiro. Olhe a estrutura de pastas do repositório (primeiro e segundo nível) para saber onde cada camada mora.
2. Divida em passos seguindo `references/passos.md`. Um passo é uma parte do pedido que dá para testar sozinha; o que outra parte usa vem antes.
3. Para cada passo, escreva os `criterios` seguindo `references/criterios.md`: o que o passo entrega, cada um verificável por teste. São o contrato do Tests, dos builders e dos revisores.
4. Para cada passo, liste em `diretorios` as pastas que ele pode alterar.
5. Para cada passo, marque os 4 campos seguindo `references/campos.md`. É a parte que mais pesa: leia a referência inteira antes de marcar.
6. Grave o evento e valide.

## Regras
- **As palavras do pedido justificam cada campo**: `true` e `incerto` trazem o trecho exato do pedido.
- **Replanejar não muda o que já passou**: em `replanejar_de`, os passos anteriores ao indicado ficam exatamente como estavam.

## Saída
Evento `spec_pronta`, exemplo em `.agents/shared/exemplos/spec_pronta.json`:

```json
{"tipo": "spec_pronta", "passos": [
  {"id": 1, "descricao": "...", "criterios": ["...", "..."], "diretorios": ["api/"],
   "campos": {"interface":  {"valor": false},
              "servidor":   {"valor": true, "trecho": "palavras exatas do pedido"},
              "agente_llm": {"valor": false},
              "seguranca":  {"valor": "incerto", "trecho": "palavras exatas do pedido"}}}]}
```

Grave no arquivo indicado na chamada, só o JSON, sem cerca de markdown, e rode:
`python .agents/shared/validar.py spec_pronta <arquivo>`. Só entregue se passar.

## Dúvida ou falta de informação
- Falta informação que está no repositório ou na web: termine com `explorar_solicitado` (pergunta, onde procurar e para quê). O Orchestrator chama o Explorer e retoma você com a resposta.
- O pedido é ambíguo de um jeito que muda o resultado: termine com `duvida_contrato` (pergunta curta e o que muda conforme a resposta). Não chute: o fluxo pausa até o humano responder.

## Nunca decide
- Quem atua: você marca os campos; o Orchestrator liga os atores e decide os `incerto`.
- Como implementar cada passo.
- O campo `decisao`: fica sempre vazio na sua saída. O formato recusa se vier preenchido.
