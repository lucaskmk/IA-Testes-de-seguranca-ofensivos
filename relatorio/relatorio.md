# Testes de segurança ofensivos com apoio de IA
### Agente supervisionado contra o OWASP Juice Shop

**Avaliação Final — Tecnologias Hackers (Insper, 2026.2) · Prof. Rodolfo Avelino**
Grupo 6 — Lucas Kamikawa e Raphael Barbuti

> Nota: a redação deve ser revisada pela dupla antes da entrega. Converter para PDF (4 a 6 páginas) e inserir os prints indicados por `[figura]`. A declaração de uso de IA (seção 1) fica para a dupla preencher conforme a orientação do professor.

---

## 1. Introdução, escopo e ética

Este trabalho investiga **em quais situações um modelo de linguagem local contribui para um teste de segurança, onde falha e quando a intervenção humana continua necessária** — e não em maximizar o número de vulnerabilidades. Construímos um agente supervisionado que integra o modelo `qwen3:4b` (via Ollama) a quatro ferramentas controladas e o usamos para conduzir três investigações numa instância local do OWASP Juice Shop.

Todo o ambiente roda no kit de laboratório, restrito à instância local (`juiceshop:3000`); o agente não alcança serviços externos, a LAN, o pfSense ou máquinas de outros grupos. O isolamento foi verificado e está documentado (seção 2).

*[Declaração de uso de IA externa — a dupla preenche conforme a orientação do professor.]*

## 2. Arquitetura do laboratório e do agente

**Laboratório.** Tudo roda no Ubuntu Server 24.04 do kit (10.0.80.3), atrás do pfSense do Roteiro 1; o acesso do grupo é só pela VPN. O Juice Shop (`v20.3.0`, fixado por digest) e uma estação Kali rodam como containers numa rede Docker `internal` (`labnet`), sem rota de saída. O modelo roda no Ollama em loopback. O `lab/restore.sh` recria o Juice Shop e só o considera pronto quando a aplicação responde e o placar mostra zero desafios resolvidos; nos testes, o ambiente voltou em 3 s. `[figura: diagrama da topologia]`

**Escopo em três camadas**, cada uma com evidência:
1. **Código** (`agent/scope.py`): host e porta vêm da configuração; o modelo só escolhe path, método, cabeçalhos, corpo e flags de uma lista permitida. Teste negativo: 14/14 tentativas de saída bloqueadas (`logs/teste_escopo.jsonl`). Na prática, a trava bloqueou um payload de injeção com espaços durante a I3 (`investigacao_I3.jsonl, turno 3`).
2. **Rede** (`labnet` interna + regra `ufw`): o Kali só alcança o Juice Shop (`lab/evidencias/check_env_*.txt`, 0 falhas).
3. **Perímetro** (pfSense + VPN): sem a VPN, nem a WAN nem o servidor respondem (`lab/evidencias/isolamento_sem_vpn_*.txt`).

**Agente.** Python com a biblioteca padrão, chamando a API do Ollama. A cada turno o modelo recebe o objetivo, os fatos observados e um histórico curto, e responde em JSON validado contra um schema. A dupla então **autoriza, modifica, rejeita ou finaliza**, sempre com justificativa; proposta bloqueada pela trava não pode ser autorizada. As ferramentas (`http_request`/curl, `nmap_scan`, `dir_enum`/ffuf, `decode_jwt`) executam dentro do Kali via `docker exec`, sem shell. Cada turno é gravado em JSONL com a proposta, a justificativa do modelo, a decisão e o motivo, o comando executado, o resumo e o **SHA-256 da saída** (reconferido por `summarize_logs.py`), a interpretação do modelo e a decisão do grupo. Parâmetros fixos: temperatura 0,2, seed 42, thinking desligado. `[figura: ciclo do turno]`

## 3. Estratégia de testes

O plano foi escrito pela dupla a partir de um reconhecimento manual (9 observações datadas em `planejamento/observacoes_iniciais.md`), com três hipóteses falseáveis — uma por tema do enunciado — commitado e enviado ao remoto **antes** de qualquer revisão pelo modelo (`planejamento/plano_testes_grupo.md`, commit anterior ao da revisão). Em seguida, o próprio modelo revisou o plano (Fase 3.2): das 6 sugestões, **1 foi aceita, 3 modificadas e 2 rejeitadas** — estas por trocarem categorias que o plano já distinguia (confirma/refuta/inconclusivo). A tabela de decisões está em `planejamento/revisao_llm.md`.

## 4. Resultados das investigações

Detalhe completo (6 itens) em `investigacoes/I{1,2,3}.md`. Resumo:

**I1 — Reconhecimento (CONFIRMADA).** Hipótese: o bundle da SPA declara rotas não linkadas no menu. O `GET /main.js` (1,24 MB) revelou **45 rotas**, incluindo `administration`, `accounting`, `score-board` e `data-export`, ausentes da navegação (`investigacao_I1.jsonl, turno 2`). O modelo, porém, **não extraiu nenhuma rota** — a extração foi manual.

**I2 — Autorização (CONFIRMADA).** Com o token de uma conta comum (id 25), `GET /api/Users/1` devolveu **200 com o registro do admin** (`investigacao_I2.jsonl, turno 4`): autorização quebrada por recurso (IDOR). A hipótese secundária de JWT fraco foi **refutada** (alg RS256), mas o token expõe o hash MD5 da senha e o `totpSecret` no payload.

**I3 — Entrada (CONFIRMADA).** `q=apple` deu 200 com 3 produtos; `q=apple'` deu **500 `SQLITE_ERROR: near "'%'": syntax error`** (`investigacao_I3.jsonl, turno 3`): a busca concatena a entrada crua — SQL injection. A página de erro ainda expõe a stack (erro verboso, A05).

As três conclusões estão presas a respostas HTTP concretas, não a afirmações do modelo.

## 5. Análise crítica da contribuição da IA

Documento completo em `relatorio/analise_critica.md`. Em 13 turnos, **7 (54%) foram modificados** pela supervisão e só 2 autorizados como propostos; **as duas falhas (IDOR e SQLi) só se confirmaram por modificações humanas** (I2 turno 4, I3 turno 3). O modelo **nunca produziu JSON inválido** (0/13) e **adaptou-se a feedback** ao menos uma vez (corrigiu o endpoint de login, `investigacao_I2.jsonl, turno 3`), mas também **alucinou** endpoints (`/api/auth/login`) e campos (um "ETag" inexistente no `decode_jwt`), **repetiu** ações (I2, turnos 5–6) e **não leu** o que não coube no resumo truncado (as 45 rotas de I1). Caso de falha principal: diante do bundle de 1,24 MB, o modelo concluiu "é um JS de 1,24 MB" — percebemos ao comparar com o arquivo cru, e a extração foi humana; é a melhor evidência da diferença entre *processar* e *compreender*. Limitações separadas — **do modelo:** interpretação rasa, alucinação, repetição; **da integração:** truncamento em 3500 caracteres (fatal para saídas grandes) e latência de 31–78 s por turno.

## 6. Conclusão e limitações

O agente de 4B foi útil como **gerador supervisionado de propostas e leituras**, não como investigador autônomo: acelerou o reconhecimento e produziu material rico para a análise, mas dependeu de supervisão constante e não confirmou sozinho nenhuma falha. A nota central do trabalho é essa — a IA contribui quando um humano técnico filtra, corrige e dirige; a autonomia, aqui, seria um passivo. Limitações do estudo: três investigações e 13 turnos não sustentam estatística, só padrões qualitativos; não exploramos as falhas além da detecção; os achados secundários (MD5 no token, erro verboso) ficam para investigação própria.
