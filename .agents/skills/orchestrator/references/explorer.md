# Explorer

## Pedido (`explorar_solicitado`)
```json
{"tipo": "explorar_solicitado", "quem_chamou": "Backend", "pergunta": "onde fica a query de vendas?",
 "escopo": ["api/vendas/"], "para_que": "decidir onde aplicar o filtro de período"}
```
`para_que` é obrigatório: o Explorer responde melhor sabendo qual decisão a resposta apoia, e o trace mostra por que a busca foi feita.

## Resposta
```json
{"tipo": "explorer_resposta", "achados": [{"fonte": "api/vendas/repo.py:42", "trecho": "def listar_vendas(inicio, fim)"}], "nao_achou": false}
```
Sem achados, `nao_achou` é `true`. Todo achado tem fonte: resposta sem fonte não pode ser conferida.

## Teto
3 pedidos por papel em cada passo; o contador zera no passo seguinte e é separado por papel. O 4º pedido é recusado: diga ao papel que decida com o que tem ou que reprove o passo com o motivo.

Formatos: `.agents/shared/eventos.py` (`ExplorarSolicitado`, `ExplorerResposta`). Teto: `scripts/proximo_estado.py` (`TETO_EXPLORER`).
