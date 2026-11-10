# Roteiro do vídeo (até 10 min)

> **Provisório.** A estrutura final do vídeo segue a especificação que o professor vai enviar. Ajustar este roteiro quando ela chegar; por ora, serve de base com uma investigação completa (I2).

Alvo: ~9:30, com folga. Demonstração: **investigação I2 (autorização/IDOR)** — a mais rica em supervisão (rejeição, modificação, alucinação corrigida, a intervenção que confirma a falha e o loop). I3 (SQL injection) entra como menção forte.

> **Importante (honestidade e nota):** a dupla deve **conduzir/narrar a demo vocês mesmos** — relendo os logs e, de preferência, reexecutando a I2 ao vivo (vocês treinaram para isso). A banca vai perguntar; cada integrante deve falar em pelo menos um bloco. Cortes de espera da inferência (31–78 s por turno) devem ser **sinalizados na tela**.

Preparação antes de gravar: VPN conectada; `bash lab/ollama.sh status` ok; `bash lab/restore.sh` recém-rodado; fonte do terminal grande; logs e o painel abertos.

| Tempo | Na tela | O que dizer / mostrar | Critério |
|---|---|---|---|
| 0:00–0:40 | Título + nomes | Quem somos e a pergunta do trabalho: onde um LLM local **ajuda** numa investigação de segurança, onde **falha**, e onde a decisão humana é **indispensável**. A nota não depende do nº de falhas. | Doc |
| 0:40–1:40 | Diagrama de arquitetura (`.claude/painel.html`) | Tudo roda no kit, atrás do pfSense, acesso só por VPN. Modelo `qwen3:4b` local. **Três camadas de escopo:** allowlist no código, rede Docker interna, perímetro pfSense. O agente não tem shell. | Lab 15% · Agente 20% |
| 1:40–2:30 | Terminal: `restore.sh` e `check_env.sh` | Restore recria o Juice Shop e prova o estado inicial (0 desafios). `check_env` dá **0 falhas** e mostra que o Kali só alcança o alvo (não internet, pfSense, SSH). Mostrar o teste de isolamento sem VPN. | Lab 15% |
| 2:30–3:10 | `planejamento/` no git | Plano 3.1 escrito pela dupla, com 3 hipóteses falseáveis, **commitado e enviado antes** da revisão (mostrar o hash/horário). Revisão 3.2 pelo modelo: 6 sugestões, **1 aceita / 3 modificadas / 2 rejeitadas** — mostrar a tabela e explicar uma rejeição. | Planejamento 20% |
| **3:10–3:30** | Slide da hipótese I2 | **Hipótese:** uma conta comum consegue ler o registro de outro usuário? A API checa "está logado?" ou "este recurso é seu?". | Evidências 20% |
| **3:30–4:10** | Terminal do agente | **Turno 1:** o modelo abre com `nmap`. **Rejeitamos** — não avança a autorização (tag `acao_desnecessaria`). Explicar: supervisão não é só aprovar. | Crítica 20% |
| **4:10–5:00** | Terminal | **Turno 2:** o modelo propõe `GET /api/auth/login` com `admin/admin` — **endpoint alucinado** (não existe no Juice Shop). **Modificamos** para registrar uma conta de teste (`POST /api/Users`). Mostrar a conta criada (id 25, customer). | Crítica 20% · Agente 20% |
| **5:00–5:40** | Terminal (destacar) | **Turno 3:** o modelo **se corrige sozinho** e propõe o login certo (`POST /rest/user/login`), citando nosso feedback. **Autorizamos** → recebemos o JWT. Ponto a favor da IA: adaptação ao feedback. | Agente 20% |
| **5:40–6:40** | Terminal — o clímax | **Turno 4:** o modelo quer ler o **próprio** id (só prova autenticação). **Modificamos** para `GET /api/Users/1` (outro usuário). Resultado: **200 com o registro do admin**. **IDOR confirmado** — e a confirmação veio da intervenção humana. | Evidências 20% |
| **6:40–7:20** | Log + `decode_jwt` | **Turno 5:** inspecionamos o token. **RS256** refuta a hipótese de JWT fraco; mas o payload expõe **hash MD5 da senha** e `totpSecret`. O modelo **alucina um "ETag"** e não percebe nada disso. | Crítica 20% |
| **7:20–7:50** | Log JSON aberto | **Turnos 5–6:** o modelo entra em **loop** (repete o teste do próprio id). **Finalizamos**: **CONFIRMADA**. Mostrar no log o turno 4 que sustenta a conclusão. | Evidências 20% |
| 7:50–8:20 | Tabela-resumo I1 e I3 | **I1** (reconhecimento): 45 rotas no `main.js`, incluindo admin — o modelo não as extraiu, nós sim. **I3** (entrada): `q=apple'` → **500 SQLITE_ERROR** = SQL injection; a trava de escopo bloqueou o payload de tautologia do modelo. | Evidências 20% |
| 8:20–9:10 | Métricas + frase-tese | **54% dos turnos modificados**; **0 JSON inválido**; as duas falhas confirmadas por intervenção humana. Caso de falha: o modelo diante de um bundle de 1,24 MB concluiu "é um JS de 1,24 MB" — não leu as 45 rotas (limitação da integração + do modelo). | Crítica 20% |
| 9:10–9:30 | Slide final | Onde a IA ajudou (propostas, correção sob feedback, leitura de um erro SQL), onde falhou (alucinação, repetição, interpretação rasa) e por que a intervenção humana foi indispensável. | Crítica 20% |

## Dicas de gravação
- Gravar a demo num take separado; editar as esperas do modelo e **avisar na tela que houve corte**.
- Não ler slide: sempre apontar a evidência no terminal/log.
- Fechar notificações; fonte grande; um ensaio cronometrado antes (precisa ficar < 9:40).
- Ter o `investigacao_I2.jsonl` e o `relatorio/metricas.md` abertos para mostrar números reais.
