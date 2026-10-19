# Dado pessoal (CPF, e-mail, telefone, endereço, dado de cliente)

Reprove quando o diff:
1. **Escreve dado pessoal em log, print, trace ou mensagem de erro** sem máscara (CPF `***.***.***-12`, e-mail `a***@dominio`), e a spec não pede.
2. **Devolve mais campos do que a spec pede**: a resposta traz o registro inteiro quando a tela usa nome e e-mail.
3. **Deixa um usuário ver o dado de outro**: a busca por id ou CPF não confere a quem o dado pertence.
4. **Grava dado pessoal em arquivo, cache ou lugar novo** que a spec não pede (exportação, arquivo temporário, fila).
5. **Monta consulta com o valor do usuário concatenado** (f-string ou `+` em SQL): use parâmetros da biblioteca.

Como provar: rode o fluxo com um cliente inventado e mostre a linha do log, o campo a mais, o dado do outro dono ou a consulta alterada.
