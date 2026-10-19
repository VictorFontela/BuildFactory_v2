# O que olhar no diff do passo

Revise só o que mudou desde o commit do Tests. Código que já existia antes do passo não é do passo.

## Reprove
1. **Não faz o que a spec diz**, mesmo com os testes passando: valor fixo que só serve ao teste, caso da spec que o código ignora, regra trocada.
2. **Print ou log de depuração**: `print(`, `console.log(`, `breakpoint()`, `debugger`, `pdb`.
3. **Comentário que repete o código** (`# incrementa o contador` em cima de `contador += 1`) e **texto que não foi pedido**: docstring longa explicando o óbvio, nota, TODO, arquivo de documentação ou README que o passo não pede.
4. **Efeito colateral que a spec não pede**: gravar ou apagar arquivo, chamar rede, mudar variável global ou de ambiente.
5. **Acesso a atributo interno de outro módulo** (nome que começa com `_`) quando o módulo tem interface pública para isso.
6. **Arquivo que não foi pedido**: rascunho, cópia, script avulso, mesmo dentro dos diretórios.
7. **Código morto**: função que nada chama, bloco comentado, import sem uso.
8. **Segredo no código**: senha, token ou chave escritos no arquivo.

## Não reprove
- Gosto: nome que você daria diferente, outra forma igualmente correta, formatação.
- O que a spec não pede: funcionalidade a mais que você acharia útil.
- Código de antes do passo, mesmo ruim.

Cada reprovação desnecessária gasta uma das 2 voltas do passo. Na dúvida se é gosto, é gosto: aprove e anote na `evidencia`.

## Como achar rápido
```bash
git diff <commit do testes_red>..HEAD --stat
git diff <commit do testes_red>..HEAD
git diff <commit do testes_red>..HEAD | grep -nE '^\+.*(print\(|console\.log|breakpoint\(|debugger|pdb|TODO|open\(|requests\.|fetch\(|os\.environ)'
```
O `grep` só aponta onde olhar; quem decide é a leitura do código contra a spec.
