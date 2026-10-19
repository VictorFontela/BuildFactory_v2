# Como pedir ao Explorer

Um papel não chama outro. Quando falta informação que está no repositório ou na web, termine com o evento:

```json
{"tipo": "explorar_solicitado", "quem_chamou": "Frontend",
 "pergunta": "qual cliente HTTP a tela usa e onde ele está?",
 "escopo": ["web/src/api/"],
 "para_que": "chamar o PATCH no mesmo padrão das outras telas"}
```

- **pergunta**: uma, que tenha resposta no código ou num documento. "Como a tela chama a API?" sim; "como devo fazer?" não.
- **escopo**: o menor lugar onde a resposta deve estar (pastas, arquivos, URLs). Escopo grande custa tempo e traz achado parecido.
- **para_que**: o que você vai fazer com a resposta; é o que o Explorer usa para saber o que importa.

O Orchestrator chama o Explorer e retoma você com `explorer_resposta` (`achados` com fonte e trecho, ou `nao_achou`).
São até 3 pedidos por papel em cada passo. Depois disso, decida com o que tem; se não dá para decidir, termine com `duvida_contrato`.
