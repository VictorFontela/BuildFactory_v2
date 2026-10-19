# Como dividir um pedido em passos

Um passo é a menor parte do pedido que dá para **testar sozinha** e cujo resultado **se vê**: uma rota que responde, uma tela que mostra, um assistente que passa a fazer algo. Cada passo tem o seu próprio ciclo de teste, construção e revisão, então dividir demais custa voltas, e dividir de menos mistura defeitos.

## Como dividir

1. **Ache as partes do pedido.** Uma parte é cada coisa que o pedido pede, em geral ligada por "e": "criar X **e** mostrar Y" tem duas partes.
2. **Pedido com duas ou mais partes:** cada parte vira **um passo**, com tudo o que ela precisa junto (servidor, tela, assistente). Não separe servidor e tela de uma mesma parte.
3. **Pedido com uma parte só**, que precisa de servidor e de tela: separe em dois passos, servidor antes e tela depois. É o único caso em que camadas da mesma parte viram passos diferentes.
4. **Não divida o que não se testa separado.** Trocar um texto, uma cor ou um rótulo é um passo só, mesmo que toque mais de um arquivo.
5. **O que outra parte usa vem antes.** O formato antes de quem o lê; o login antes do que só funciona logado; o assistente antes da tela que mostra o que ele produz.
6. **No máximo 4 passos.** Se precisar de mais, o pedido é grande demais: termine com `duvida_contrato` propondo dividir em capacidades.

## Diretórios e campos combinam, nos dois sentidos

| Se o passo lista uma pasta de… | então o campo… | e se o campo não é `false` (inclusive `incerto`)… |
|---|---|---|
| servidor (`api/`, `infra/`) | `servidor` não pode ser `false` | liste uma pasta de servidor |
| tela (`web/`) | `interface` não pode ser `false` | liste uma pasta de tela |
| assistente (`agent/`) | `agente_llm` não pode ser `false` | liste uma pasta do assistente |

O segundo sentido importa porque, se o Orchestrator decidir um `incerto` como `true`, o builder é chamado e só pode mexer nas pastas listadas. Campo ligado sem pasta deixa o builder sem onde trabalhar.

A descrição diz o resultado que se vê, em uma frase, com o nome da parte do pedido ("Exportar tarefas em CSV", não "Ajustes no backend").

## Replanejar

Ao receber `replanejar_de: N`, copie os passos 1 a N−1 da spec anterior **exatamente** como estavam, campo por campo, e refaça só do passo N em diante, seguindo a instrução do humano. O script recusa a spec que altera um passo anterior.

## Exemplos

| Pedido | Partes | Passos |
|---|---|---|
| Tela de relatório de vendas por loja, com gráfico | 1 | 1 · Endpoint de vendas por loja (`api/`) → 2 · Tela com o gráfico (`web/`) |
| Corrigir o texto do botão na tela de login | 1 | 1 · Texto do botão corrigido (`web/`) |
| Cadastrar clientes e buscar clientes pelo nome | 2 | 1 · Cadastro de clientes (`api/`, `web/`) → 2 · Busca de clientes pelo nome (`api/`, `web/`) |
| Nova tool do agente: consultar estoque, e mostrar o estoque no chat | 2 | 1 · Tool de consulta de estoque (`agent/`, `api/`) → 2 · Estoque exibido no chat (`web/`) |
