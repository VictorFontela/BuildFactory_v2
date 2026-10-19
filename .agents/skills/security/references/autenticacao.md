# Login, senha, token, permissão

Reprove quando o diff:
1. **Guarda ou compara senha em texto puro.** Senha se guarda com hash lento e sal (bcrypt, argon2, scrypt, pbkdf2) e se compara pelo hash.
2. **Compara segredo com `==`** (senha, token, código): use a comparação em tempo constante da linguagem (`hmac.compare_digest`, `crypto.timingSafeEqual`).
3. **Põe senha, token ou hash em log, mensagem de erro, resposta ou exceção.**
4. **Diz qual parte errou** ("usuário não existe" vs "senha errada") quando a spec não pede isso: o atacante descobre quais usuários existem.
5. **Não confere permissão no servidor**: a regra de quem pode fazer o quê só na tela, ou o id do dono vindo do cliente em vez da sessão.
6. **Token sem validade ou que não é conferido** (assinatura, expiração, a quem pertence).
7. **Segredo no código**: chave, senha de banco, token fixo.

Como provar: chame a função com credenciais inventadas e mostre o log, a resposta ou o acesso que não devia acontecer.
