# Seleção por regras (variante)

Igual à seleção híbrida, mas sem `"incerto"`: cada campo é `true` ou `false`, preenchido pela Specification, e a regra campo → ator é aplicada sem LLM.

Vantagem: o Orchestrator não chama LLM para escolher atores; mesma entrada, mesma saída.
Custo medido na 2a: acerto de 6 em 10 contra 9 em 10 da híbrida. Os erros foram todos Backend esquecido, quando a spec não dizia em palavras que havia trabalho no servidor (recall de Backend 0,43).

Use esta variante só para comparação na Etapa 5.
