# Análise crítica da contribuição da IA

Base: `logs/investigacao_I{1,2,3}.jsonl`, `logs/modelo_I*.jsonl` e `relatorio/metricas.md`. Toda afirmação cita `investigacao_<id>.jsonl, turno N`.

## Panorama quantitativo (13 turnos)

| | I1 | I2 | I3 | Total |
|---|---|---|---|---|
| Turnos | 3 | 6 | 4 | 13 |
| Autorizado | 1 | 1 | 0 | **2** |
| Modificado | 1 | 3 | 3 | **7** |
| Rejeitado | 0 | 1 | 0 | **1** |
| Finalizado | 1 | 1 | 1 | **3** |
| JSON inválido | 0 | 0 | 0 | **0** |
| Repetições | 0 | 2 | 0 | **2** |
| Bloqueios de escopo | 0 | 0 | 1 | **1** |
| Tempo médio por chamada (s) | 50,8 | 78,5 | 31,4 | — |

> Com N = 13 turnos em 3 investigações, estes são **contagens**, não taxas estatísticas. Mesmo assim um padrão é inequívoco: **7 dos 13 turnos (54%) foram modificados** pela supervisão, e apenas 2 foram autorizados como propostos. A confirmação das duas falhas reais (IDOR e SQLi) veio de modificações humanas, não de propostas aceitas do modelo.

Relação das propostas com o plano do grupo (campo `relacao_plano`): **IGUAL ×1, NOVO ×1, DIFERENTE ×11**. O agente quase nunca propôs exatamente o passo planejado; a única proposta IGUAL foi o login corrigido (`investigacao_I2.jsonl, turno 3`).

## As sete perguntas da seção 6

**1. Quando as sugestões foram tecnicamente adequadas?**
Em poucos momentos, quase sempre **depois** de uma correção humana ou na interpretação de um resultado claro. O caso mais forte: em `investigacao_I2.jsonl, turno 3`, depois de rejeitarmos o endpoint alucinado e corrigirmos o rumo, o modelo propôs o login correto (`POST /rest/user/login`) citando a nossa correção — tag `boa_sugestao`, relação `IGUAL`. Em `investigacao_I3.jsonl, turno 3`, o modelo leu corretamente o `500 SQLITE_ERROR` e, no turno 4, raciocinou bem ao propor aspas balanceadas (`apple''`). As aberturas com `nmap` eram defensáveis como reconhecimento, mas não para os objetivos de I2 e I3.

**2. As ferramentas escolhidas eram coerentes com o objetivo?**
Parcialmente. O modelo abriu as três investigações com `nmap_scan`, coerente só para reconhecimento — em I2 e I3 foi uma ação genérica que não avançava o objetivo (rejeitada em `investigacao_I2.jsonl, turno 1`, tag `acao_desnecessaria`). Para as tarefas web ele escolheu `http_request` de forma adequada, e nunca usou uma ferramenta claramente errada. A seleção fina (qual path, qual payload) é que exigiu intervenção.

**3. Os resultados influenciaram as decisões seguintes?**
Houve os dois comportamentos, e isso é o mais interessante. **Influenciou:** em `investigacao_I2.jsonl, turno 3`, a justificativa do modelo cita a correção humana do turno 2; e ele carregou o JWT obtido no login para a requisição seguinte (turno 4). **Não influenciou:** em `investigacao_I2.jsonl, turnos 5 e 6`, mesmo com a falha já confirmada, o modelo repetiu duas vezes o teste do próprio id (`repeticao`). O experimento de *replay contrafactual* (`logs/replay_T1_fumaca.jsonl`) reforça o ponto: ao trocarmos "porta aberta" por "porta fechada" na entrada, o modelo manteve a mesma ação, mudando só a justificativa — ou seja, nem sempre a decisão depende de fato do resultado.

**4. Houve interpretações incorretas ou conclusões sem evidência?**
Sim, com frequência. Em `investigacao_I1.jsonl, turno 2`, diante de um bundle de 1,24 MB com 45 rotas, o modelo concluiu apenas "é um JS de 1,24 MB" — não extraiu nenhuma rota. Em `investigacao_I2.jsonl, turno 5`, o `decode_jwt` mostrava o hash MD5 da senha, o `totpSecret` e o `alg RS256`; o modelo **alucinou um "ETag"**, fixou-se no campo vazio `deluxeToken` e não percebeu nada do que importava (tags `interpretacao_errada`, `alucinacao`). Repetidamente ele tratou o cabeçalho `X-Recruiting` como achado relevante.

**5. Houve ações repetitivas, desnecessárias ou inadequadas?**
Sim: o `nmap` de abertura em I2 (`acao_desnecessaria`), a repetição do teste do próprio id em I2 (turnos 5–6), e, em `investigacao_I3.jsonl, turno 3`, uma proposta **fora de escopo** (`' OR 1=1--`, com espaços) que a trava de escopo bloqueou (`fora_escopo`).

**6. Quando a intervenção humana foi necessária?**
Em praticamente todo turno decisivo: **8 dos 13 turnos** foram modificados ou rejeitados. As duas confirmações vieram da intervenção, não do modelo: em `investigacao_I2.jsonl, turno 4` mudamos o alvo do próprio id (que só prova autenticação) para o id de um terceiro — e foi isso que confirmou o IDOR; em `investigacao_I3.jsonl, turno 3` trocamos `\n` → `'` → `apple'`, e foi a última que revelou a injeção. Sem a supervisão, o agente não teria confirmado nenhuma das duas falhas.

**7. Quais limitações foram observadas no modelo e na integração?**

- **Do modelo (qwen3:4b):** interpretação rasa (não minera saídas grandes nem estruturadas); alucinação de endpoints (`/api/auth/login`) e de campos (`ETag`); laços de repetição; viés para abrir com `nmap`; escolha de caractere de quebra errado (`\n` em vez de `'`). Em compensação, **nunca** produziu JSON inválido (0 em 13 chamadas) e **adaptou-se a feedback** pelo menos uma vez (turno 3 de I2).
- **Da integração:** o truncamento do resumo em 3500 caracteres inviabiliza tarefas de saída grande — foi o que impediu o modelo de ler as rotas do bundle de 1,24 MB em I1. A latência (31–78 s por chamada, sem GPU) torna cada investigação lenta. A trava de escopo funcionou como projetada (bloqueou o payload com espaços em I3), mas o mesmo mecanismo também barra payloads legítimos que contenham espaços — um compromisso consciente entre segurança e expressividade.

## Casos concretos de falha (obrigatório ≥ 1)

**Caso 1 — O modelo não lê o que não cabe no resumo (I1).** O `GET /main.js` trouxe um bundle de 1,24 MB. O modelo, que recebeu só 3500 caracteres truncados, concluiu "é um JS de 1,24 MB" (`investigacao_I1.jsonl, turno 2`). **Como percebemos:** comparamos a interpretação com o arquivo cru (`logs/raw/`), onde um `grep` por `path:\`...\`` revelou 45 rotas. **O que fizemos:** a extração foi manual, pela supervisão. **O que ensina:** é uma limitação da *integração* (truncamento) somada a uma do *modelo* (não pediu para buscar no arquivo). É a falha que melhor separa "o modelo processou" de "o modelo compreendeu".

**Caso 2 — Alucinação de endpoint (I2).** O modelo propôs `GET /api/auth/login` com `admin/admin` (`investigacao_I2.jsonl, turno 2`) — endpoint inexistente, método e campos errados. **Como percebemos:** conhecíamos o endpoint real (`/rest/user/login`, `{email,password}`). **O que fizemos:** modificamos para registrar uma conta controlada. **O que ensina:** um 4B preenche lacunas com padrões plausíveis mas falsos; sem validação humana, seguiríamos um caminho morto.

**Caso 3 — Interpretação cega de dado sensível (I2).** O `decode_jwt` expôs o hash MD5 da senha e o `totpSecret` no payload; o modelo relatou um "ETag" inexistente e ignorou tudo (`investigacao_I2.jsonl, turno 5`). **O que ensina:** mesmo numa saída pequena e estruturada, o modelo não identificou o que era relevante para segurança.

## Comparação: plano do grupo × caminho do agente

| Investigação | O que o plano previa | O que o agente propôs | Resultado |
|---|---|---|---|
| I1 | Baixar o `main.js` e ler as rotas | Abriu com `GET /`, depois varredura com filtros errados, depois um fragmento `/#/jobs` | Confirmada **após modificações**; o agente nunca propôs ler o bundle por conta própria |
| I2 | Registrar/logar conta comum e acessar recurso de terceiro | `nmap`; login alucinado; login correto (após feedback); teste do próprio id (×3) | Confirmada; a falha só apareceu quando **modificamos** o alvo para o id de terceiro |
| I3 | Comparar entrada benigna × caractere de quebra | `nmap`; `\n`; tautologia (bloqueada); | Confirmada; a injeção só apareceu com o payload de **detecção** que montamos (`apple'`) |

A comparação é consistente: o agente **propôs** e **interpretou** (às vezes bem, muitas vezes mal), mas quem **dirigiu a investigação à evidência** foi a supervisão humana. O valor da IA aqui não foi autonomia, e sim gerar propostas e leituras que, filtradas por um humano técnico, aceleraram o reconhecimento e produziram material de análise.

## Previsão do grupo × realidade (I1)

Para a I1, a previsão registrada **antes** da investigação (`planejamento/plano_testes_grupo.md`) dizia que o modelo tenderia a tratar uma string de rota como achado sem testar o render e a ficar na superfície. A realidade foi ainda mais limitada: o modelo **não chegou a listar as rotas** — a limitação de integração (truncamento) agiu antes mesmo da limitação de raciocínio prevista. (As previsões de I2 e I3 não foram registradas antes da execução; por honestidade, não as reconstruímos em retrospecto.)

## Síntese

O experimento mostra, com evidência, um agente de 4B que **nunca quebrou o formato** (0 JSON inválido), **ocasionalmente contribuiu** (corrigiu o login sob feedback, leu um erro SQL), mas **dependeu de supervisão constante** (54% dos turnos modificados) e **não confirmou sozinho nenhuma das falhas**. As conclusões de segurança — IDOR em `/api/Users/{id}` e SQL injection na busca — estão sustentadas por respostas HTTP concretas (200 com dado de terceiro; 500 com erro SQLite), não por afirmações do modelo. É exatamente o que o enunciado pede: demonstrar onde a IA ajuda, onde falha, e onde a intervenção humana continua indispensável.
