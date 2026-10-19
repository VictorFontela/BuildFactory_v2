# Estouro das 2 voltas

## Quando
O passo já tem `t = 2` e chega uma nova reprovação.

## O que fazer
Pause em **Escalar** e entregue ao humano um pacote com:
- o passo e a spec dele;
- o histórico das voltas: para cada uma, quem reprovou, o motivo, o destino e o porquê;
- a última reprovação, que causou o estouro;
- as 3 saídas, e o que cada uma faz:

| Saída | Vai para | Use quando |
|---|---|---|
| `mais_uma_volta` | o mesmo passo, com a instrução do humano | o defeito é pequeno e o humano sabe a correção |
| `replanejar` | Specification, a partir deste passo | o passo estava mal definido |
| `abortar` | ◉ falhou | não vale continuar |

Passos aprovados antes deste continuam valendo em qualquer saída.

## Por que escalar
Na 3b, abortar direto não entrega os passos aprovados, e seguir com o passo marcado faz o passo seguinte ser construído sobre um defeito. Escalar foi a única opção sem os dois problemas. O teste de beco sem saída mostrou que o Escalar antigo, sem saídas, travava o fluxo.

## Em aberto
Ainda não há teto para `mais_uma_volta`. Até haver, registre no trace cada vez que o humano escolhe essa saída.
