# Ao reprovar (Reviewer, QA, Security)

```json
{"tipo": "reprovacao", "passo": 1, "reprovou": "Reviewer",
 "motivo": "api/tarefas.py:14 imprime a tarefa (print de depuração); api/tarefas.py:20 grava tarefas.log, que a spec não pede",
 "arquivos": ["api/tarefas.py"], "destino": ["Backend"],
 "porque": "sobras da depuração ficaram no commit"}
```

- **motivo**: o que está errado, de um jeito que dê para conferir: `arquivo:linha` e o que acontece. Um problema por item, todos na mesma reprovação.
- **arquivos**: os arquivos que precisam mudar.
- **destino**: quem corrige.
  - O builder dono do arquivo com o defeito: veja `arquivos` de cada `build_pronto` em `builds`.
  - Mais de um builder só quando o defeito está nos arquivos de cada um.
  - `Tests` quando o teste está errado: pede o que a spec não diz ou contradiz a spec, e o código segue a spec. Diga no motivo qual teste e qual trecho da spec.
  - Só papéis que atuam no passo; o script devolve a reprovação para você corrigir se o destino não atua.
- **porque**: a causa, em uma frase, sem repetir o motivo. É o que ajuda quem corrige a não repetir o erro.

Não reprove por gosto. Cada reprovação aceita conta uma volta, e o passo tem 2 antes de ir para o humano.
