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
Abortar direto perde os passos aprovados; seguir com o passo marcado constrói o próximo sobre um defeito. Escalar evita os dois.
