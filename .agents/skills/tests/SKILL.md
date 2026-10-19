---
name: tests
description: "Papel Tests do fluxo multiagente: escreve os testes de um passo antes do código e prova que falham pelo motivo certo (red). Use só quando o Orchestrator chamar este papel como subagente, com um arquivo de entrada."
---

# Tests (TDD)

**Missão.** Escrever os testes do passo antes de qualquer código e provar que falham pelo motivo certo.

## Entrada
O passo da `spec_pronta` e os builders ativos nele; ou `reprovacao` com destino Tests, quando um revisor aponta teste errado.

## Passos
1. Leia o passo inteiro: descrição, critérios e trechos da spec. Se o passo não tem critério que dê para testar, termine com `duvida_contrato`.
2. Escreva os testes da camada de cada builder ativo, seguindo `references/por-camada.md` e as regras abaixo.
3. Faça commit local só dos arquivos de teste.
4. Rode o `rodar_red.py` (abaixo). Ele roda os testes, aceita só falha por assert (recusa erro de import, sintaxe ou coleta, e testes que já passam), confere o commit e grava o evento com `falhas` e `commit` preenchidos por ele.
5. Se ele recusar, corrija o que a mensagem diz e rode de novo.
6. Em reprovação, corrija só o teste apontado, com novo commit, e rode o script de novo.

```bash
python .agents/skills/tests/scripts/rodar_red.py --passo <n> \
  --comando "<comando que roda os testes e grava JUnit XML>" --junit <caminho do XML> \
  --arquivos <arquivos de teste> --evento <arquivo do evento>
```

Grave o JUnit XML numa pasta fora do git, como `.agents/state/`. pytest: `--junitxml=<caminho>`; jest: `jest-junit` com `addFileAttribute`; vitest: `--reporter=junit --outputFile=<caminho>`; node:test: `--test-reporter=./.agents/shared/reporters/junit-node.mjs --test-reporter-destination=<caminho>`. Passo com testes em duas linguagens: um comando que roda as duas e os dois caminhos em `--junit`.

## Regras para os testes

1. **Pelo menos um teste por critério**, com um nome que diga o critério (`test_status_invalido_levanta_valueerror`).
2. **Teste os limites que a spec nomeia**: "exatamente", "mais de", "vazio", "além do fim", "inválido", "outro usuário". É neles que o defeito costuma morar.
3. **Confira o efeito, não só o retorno.** Se a função grava, apaga ou muda algo, confira o estado depois.
4. **Não teste o que a spec não diz.** Ordem, formato, mensagem de erro ou detalhe interno que a spec não define deixam o teste reprovar código certo, e isso manda o builder corrigir o que não está errado.
5. **Use só a interface pública do passo** (as funções, rotas ou componentes que a spec ou o esqueleto definem). Se a interface ainda não existe, defina-a no próprio teste, com nomes simples, e ela vira o contrato dos builders.
6. **Cada teste monta os próprios dados**, pequenos e explícitos, e não depende de outro teste.

Evento `testes_red`: `passo, arquivos, comando, falhas, commit`; exemplo em `.agents/shared/exemplos/testes_red.json`.
Quem grava e valida o evento é o `rodar_red.py`: use o arquivo indicado na chamada em `--evento`. Não escreva o evento à mão.

## Dúvida ou falta de informação
- Falta informação que está no repositório ou na web: termine com `explorar_solicitado` (como pedir: `.agents/shared/guias/pedir-explorer.md`). O Orchestrator chama o Explorer e retoma você com a resposta.
- O contrato está errado, ou falta uma decisão que muda o resultado: termine com `duvida_contrato` (pergunta curta e o que muda no resultado). O fluxo pausa até o humano responder; não conta volta.

## Nunca decide
- O código de produção.
- Se o passo está bem definido: se não der para testar, termine com `duvida_contrato`.
