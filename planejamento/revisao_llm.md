# Revisão do plano pelo LLM (Fase 3.2)

- Plano revisado: `planejamento/plano_testes_grupo.md`, commit `c4174d5953cf661472d0deecd51f34f10bfe2d14 2026-11-05T09:16:21-03:00`
- Chamada registrada em `logs/revisao_plano.jsonl` (2026-11-05T09:22:18-03:00, 92 s, modelo qwen3:4b, seed 42)

## Decisões do grupo

| # | Parte do plano | Tipo | Sugestão do modelo | Decisão (aceita/modificada/rejeitada) | Justificativa técnica |
|---|---|---|---|---|---|
| 1 | Fora de escopo | risco | Risco de testes de autenticação com tokens inválidos ou sem permissão (motivo do modelo: O plano menciona que não alterar nem exfiltrar dados reais de outros usuários, mas não especifica como garantir que os tokens usados para autenticação sejam válidos ou com permissões adequadas, o que pode levar a testes falhos ou ineficientes.) | Rejeitada | Não é lacuna de escopo. A I2 usa uma conta comum criada por nós, com token válido; a validade do token é detalhe de execução, não de escopo. O escopo já limita o teste a `juiceshop:3000` e ao mínimo que comprova o acesso. |
| 2 | Hipótese (se… então… porque…) | hipotese | Se o parâmetro `q` é usado para filtrar produtos com base em um campo específico, então espero que um caractere de quebra em `q` altere a consulta SQL do backend, resultando em erro de sintaxe ou retorno anômalo (motivo do modelo: A hipótese atual foca apenas no tratamento de caracteres de quebra, mas não considera que a busca pode estar usando um campo específico (como `name`) que, ao ser concatenado, pode não gerar erros de sintaxe, mas sim resultados incompletos ou filtros específicos.) | Modificada | O ponto já está no plano: o critério inconclusivo da I3 é "muda o número de resultados sem erro". Reconhecemos como alternativa válida, mas a sugestão não acrescenta além do que a célula já previa — sinal de que o modelo não leu o inconclusivo. |
| 3 | Evidência que confirma | evidencia | O retorno do backend com um JSON que inclui campos como `error` ou `message` quando a consulta falha (motivo do modelo: A evidência atualmente menciona erros como 500 ou erro de sintaxe, mas não considera que o backend pode retornar uma resposta JSON com detalhes específicos de erro, o que é mais útil para diagnóstico.) | Aceita | Refina o confirma da I3: além do status 500, registrar o corpo JSON do erro (campos como `error`/`message`), evidência mais específica de falha na camada de consulta. |
| 4 | Ferramentas do agente úteis e que evidência cada uma produz | ferramenta | Use `ffuf` para realizar um scan de rotas não documentadas no backend (motivo do modelo: O plano menciona `curl` e `http_request` para testes, mas não inclui `ffuf` para explorar rotas não documentadas, o que é relevante para investigar a superfície da aplicação além do que está no bundle do front-end.) | Modificada | Em escopo (temos `dir_enum`/ffuf), mas é técnica distinta: enumeração no servidor, não descoberta pelo cliente. Entra como passo complementar da I1, sem substituir a leitura do bundle, e filtrando por tamanho por causa do comportamento SPA (obs. 8). |
| 5 | Matriz das investigações | lacuna | Não considerar a possibilidade de autenticação por token JWT em vez de autenticação por senha (motivo do modelo: O plano foca em autenticação por conta comum, mas não aborda a possibilidade de tokens JWT sendo usados para autorização, o que é relevante para investigações de segurança em aplicações modernas.) | Modificada | A conta comum da I2 já autentica via JWT; a sugestão confunde isso com senha. Aproveitamos para registrar que o JWT é o mecanismo de sessão e pode ser inspecionado com `decode_jwt` se um token aparecer numa resposta. |
| 6 | Evidência que refuta | evidencia | O parâmetro `q` retorna um JSON com um campo `results` vazio ou com um número reduzido de resultados (motivo do modelo: A evidência atualmente menciona que o caractere de quebra pode voltar 200 tratado como texto literal, mas não considera que a busca pode retornar resultados incompletos ou vazios, o que é um sinal de tratamento inadequado da entrada.) | Rejeitada | O modelo rotulou como "refuta" o que o nosso plano já classifica como "inconclusivo" (resultados reduzidos/vazios sem sinal da camada de consulta). Mantemos a distinção; a sugestão troca as categorias. |

## Resposta bruta do modelo

```json
{"sugestoes": [
  {
    "parte_do_plano": "Fora de escopo",
    "tipo": "risco",
    "sugestao": "Risco de testes de autenticação com tokens inválidos ou sem permissão",
    "motivo": "O plano menciona que não alterar nem exfiltrar dados reais de outros usuários, mas não especifica como garantir que os tokens usados para autenticação sejam válidos ou com permissões adequadas, o que pode levar a testes falhos ou ineficientes."
  },
  {
    "parte_do_plano": "Hipótese (se… então… porque…)",
    "tipo": "hipotese",
    "sugestao": "Se o parâmetro `q` é usado para filtrar produtos com base em um campo específico, então espero que um caractere de quebra em `q` altere a consulta SQL do backend, resultando em erro de sintaxe ou retorno anômalo",
    "motivo": "A hipótese atual foca apenas no tratamento de caracteres de quebra, mas não considera que a busca pode estar usando um campo específico (como `name`) que, ao ser concatenado, pode não gerar erros de sintaxe, mas sim resultados incompletos ou filtros específicos."
  },
  {
    "parte_do_plano": "Evidência que confirma",
    "tipo": "evidencia",
    "sugestao": "O retorno do backend com um JSON que inclui campos como `error` ou `message` quando a consulta falha",
    "motivo": "A evidência atualmente menciona erros como 500 ou erro de sintaxe, mas não considera que o backend pode retornar uma resposta JSON com detalhes específicos de erro, o que é mais útil para diagnóstico."
  },
  {
    "parte_do_plano": "Ferramentas do agente úteis e que evidência cada uma produz",
    "tipo": "ferramenta",
    "sugestao": "Use `ffuf` para realizar um scan de rotas não documentadas no backend",
    "motivo": "O plano menciona `curl` e `http_request` para testes, mas não inclui `ffuf` para explorar rotas não documentadas, o que é relevante para investigar a superfície da aplicação além do que está no bundle do front-end."
  },
  {
    "parte_do_plano": "Matriz das investigações",
    "tipo": "lacuna",
    "sugestao": "Não considerar a possibilidade de autenticação por token JWT em vez de autenticação por senha",
    "motivo": "O plano foca em autenticação por conta comum, mas não aborda a possibilidade de tokens JWT sendo usados para autorização, o que é relevante para investigações de segurança em aplicações modernas."
  },
  {
    "parte_do_plano": "Evidência que refuta",
    "tipo": "evidencia",
    "sugestao": "O parâmetro `q` retorna um JSON com um campo `results` vazio ou com um número reduzido de resultados",
    "motivo": "A evidência atualmente menciona que o caractere de quebra pode voltar 200 tratado como texto literal, mas não considera que a busca pode retornar resultados incompletos ou vazios, o que é um sinal de tratamento inadequado da entrada."
  }
]}
```
