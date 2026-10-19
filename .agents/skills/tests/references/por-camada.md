# Como testar cada camada

Em todas: teste pelo que o passo promete a quem usa, não pelo jeito de implementar. Monte os dados no próprio teste, pequenos e explícitos. Nunca chame serviço pago, rede ou banco real.

## Regra do servidor (função, serviço, repositório)
- Chame a função pública do passo e confira **o valor devolvido e o estado depois** (o que ficou gravado, o que sumiu). Conferir só o retorno deixa passar o código que devolve certo e não grava.
- Erro prometido: `pytest.raises(<a exceção da spec>)`. Não confira a mensagem, a não ser que a spec diga qual é.
- Datas: use datas fixas no teste. Só compare com `date.today()` quando a spec disser "hoje".

## Rota (HTTP)
- Use o cliente de teste do framework (FastAPI `TestClient`, Flask `test_client`), sem subir servidor.
- Confira status e corpo; para erro, o status que a spec define.

## Tela
- Renderize o componente e interaja como o usuário (Testing Library: `getByRole`, `getByText`, `userEvent`).
- Confira o que aparece na tela, não classes CSS nem estado interno.
- A chamada à API é substituída por um dublê que devolve dados fixos.

## Assistente (LLM)
- Teste o que o código faz com a resposta do modelo: montar o prompt, ler a resposta, chamar a tool certa. A resposta do modelo vem gravada num arquivo de exemplo.
- Qualidade da resposta é eval, não teste unitário: casos fixos, critério escrito antes, e o modelo real só com autorização (é chamada paga).
