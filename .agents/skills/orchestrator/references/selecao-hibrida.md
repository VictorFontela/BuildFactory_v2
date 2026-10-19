# Seleção híbrida (peça ativa)

## Entrada
A Specification entrega, para cada passo, 4 campos. Cada campo tem `valor` (`true`, `false` ou `"incerto"`) e `trecho` (palavras exatas da spec que justificam).

| Campo | Significa | Ator |
|---|---|---|
| `interface` | muda algo que o usuário vê ou usa na tela | Frontend |
| `servidor` | muda rota, API, query, banco, infraestrutura ou outro código do servidor | Backend |
| `agente_llm` | muda prompt, tool ou a forma de chamar o LLM | AI |
| `seguranca` | envolve autenticação, dado pessoal ou dar a um LLM acesso a dados | Security |

## Regra
- `true` → o ator atua. `false` → não atua.
- `"incerto"` → você decide `true` ou `false` e escreve em `decisao`, com o `trecho` da spec que levou à decisão.

## Como decidir um incerto
Pergunte: para entregar o que a spec pede, alguém precisa mexer nessa camada, mesmo que a spec não diga? Uma tela de relatório quase sempre precisa de um endpoint que entregue os dados; um login por SSO quase sempre troca token no servidor. Se a resposta for sim, `true`.

Chame quando houver trabalho concreto naquela camada, não por precaução: "na dúvida, chama" põe, por exemplo, Frontend num pedido que só muda o formato da resposta do agente.

## Exemplo
Spec: "Tela de relatório de vendas por loja, com gráfico".
```json
{"interface": {"valor": true, "trecho": "Tela de relatório de vendas por loja, com gráfico", "decisao": null},
 "servidor": {"valor": "incerto", "trecho": "relatório de vendas por loja", "decisao": true},
 "agente_llm": {"valor": false, "trecho": "", "decisao": null},
 "seguranca": {"valor": false, "trecho": "", "decisao": null}}
```
Resultado: Frontend e Backend.
