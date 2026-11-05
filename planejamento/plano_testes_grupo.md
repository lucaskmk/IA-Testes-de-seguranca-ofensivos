# Plano de testes do grupo (Fase 3.1)

Escrito pelo grupo a partir de `planejamento/observacoes_iniciais.md`. Este arquivo é commitado e enviado ao remoto antes da revisão pelo modelo (Fase 3.2); o hash e o horário desse commit são citados no relatório.

## Aspectos da aplicação que vamos investigar e por quê

Escolhemos uma investigação por situação sugerida no PDF, cada uma pressionando uma capacidade diferente do agente: (I1) o que o cliente da SPA revela da superfície, (I2) se a API autoriza por recurso ou só por autenticação, e (I3) como a busca trata uma entrada não confiável. As três partem de observações nossas do reconhecimento inicial.

## Matriz das investigações

| Campo | Investigação 1 | Investigação 2 | Investigação 3 |
|---|---|---|---|
| Situação (PDF) | Reconhecimento e enumeração | Autenticação ou autorização | Entradas, requisições ou acesso a recursos |
| Observação que motivou | Obs. 9 (front é SPA Angular, baixa tudo no bundle `main.js`) e Obs. 3 (cabeçalho `X-Recruiting: /#/jobs` vaza uma rota) | Obs. 5 (`/api/Users` deu 401 e `/api/Products` deu 200 sem login) | Rota de busca `/rest/products/search?q=` |
| Aspecto investigado | Superfície exposta pelo cliente: rotas e endpoints embarcados no bundle | Autorização por recurso versus apenas autenticação na API | Tratamento do parâmetro de busca (entrada não confiável) |
| Hipótese (se… então… porque…) | Se o cliente embarca toda a tabela de rotas no `main.js`, então espero achar no bundle um caminho não linkado em nenhum menu (ex.: área admin), porque roteamento client-side entrega ao navegador rotas que o servidor não esconde por sessão. | Se `/api/Users` existe como coleção mas exige sessão, então espero que, logado como usuário comum, um `GET /api/Users` devolva 200 com registros de outros usuários, porque o controle pode checar "está logado?" e não "tenho papel para ver a coleção toda?". | Se o parâmetro `q` é concatenado numa consulta no backend, então espero que um caractere de quebra em `q` altere a resposta (500 / erro de banco, ou conjunto anômalo) em vez de ser tratado como texto, porque a entrada pode não estar parametrizada. |
| Evidência que confirma | A string de uma rota admin aparece no `main.js`, não referenciada em nenhum menu | 200 com e-mails/ids que não são os meus | `q` normal → 200; `q` com caractere de quebra → 500 / erro de sintaxe; registrar também o corpo JSON do erro (campos `error`/`message`), não só o status (revisão 3.2, sugestão 3) |
| Evidência que refuta | Nenhuma rota não linkada no bundle; só as que aparecem na navegação | 403, ou 200 só com o meu próprio registro | O caractere volta 200 tratado como texto literal |
| Resultado inconclusivo seria | Acho a string mas não dá para saber se é rota servida ou resíduo de build | 200 com lista vazia / campos mascarados | Muda o número de resultados, sem erro nem sinal da camada de consulta |
| Ferramentas do agente úteis e que evidência cada uma produz | `http_request` baixa o `main.js` → evidência é a lista de rotas no texto. Passo complementar (revisão 3.2, sugestão 4): `dir_enum` (ffuf) com filtro por tamanho para rotas servidas pelo backend e não referenciadas no bundle | `http_request` autenticado com token de conta comum → evidência é o par (status, corpo); dado de terceiro no corpo é o que confirma. Se um JWT aparecer numa resposta, `decode_jwt` inspeciona header/payload (revisão 3.2, sugestão 5) | `http_request` variando só `q` entre valor benigno e um com caractere de quebra → evidência é o diff de (status, corpo) entre as duas |
| Como faríamos manualmente | — a dupla preenche — | — a dupla preenche — | — a dupla preenche — |
| Conteúdo da disciplina relacionado | — a dupla preenche — | — a dupla preenche — | — a dupla preenche — |
| Fora de escopo | Qualquer host fora de `juiceshop:3000`; abrir a rota no navegador para julgar o render fica como passo manual do grupo, não do agente | Qualquer host fora de `juiceshop:3000`; não alterar nem exfiltrar dados reais de outros usuários além do mínimo que comprova o acesso | Qualquer host fora de `juiceshop:3000`; não derrubar o serviço nem extrair a base; parar no sinal de erro |
| Objetivo que será entregue ao agente (sem a hipótese) | Mapear a superfície da aplicação a partir do que o cliente recebe: identificar rotas e endpoints referenciados no código do front servido ao navegador. | Avaliar se a API aplica autorização por recurso ou apenas autenticação, usando uma conta comum autenticada. | Avaliar como a funcionalidade de busca de produtos trata a entrada do parâmetro de consulta. |

> Nota de método (I1): o `http_request` usa `curl` e não executa o Angular, então ele confirma a **descoberta** da rota no bundle, não o render. Verificar se a rota renderiza/funciona é passo manual do grupo pelo navegador (túnel SSH) ou cai na investigação de autorização (I2).

## Previsão do grupo sobre a IA

Preencher **antes** de rodar a revisão 3.2 e as investigações (é a nossa aposta sobre o modelo, feita sem ele).

| Investigação | Onde esperamos que o modelo ajude | Onde esperamos que erre | Intervenção que achamos que vamos precisar |
|---|---|---|---|
| 1 | Varrer o `main.js` e listar rápido as rotas do roteamento, inclusive paths não linkados no menu (ex.: área admin) — trabalho mecânico de busca em bundle grande | Tratar uma string de rota como achado sem testar o render; confundir resíduo de build / rota morta com endpoint servido; afirmar que um path é acessível sem checar guard client-side ou gate no servidor | A lista do bundle não é prova sozinha: o veredito de "acessível" exige abrir a rota no navegador e ver o status de render — passo manual nosso |
| 2 | — a dupla preenche — | — a dupla preenche — | — a dupla preenche — |
| 3 | — a dupla preenche — | — a dupla preenche — | — a dupla preenche — |
