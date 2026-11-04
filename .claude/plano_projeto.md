# Plano do projeto — AF Tecnologias Hackers (26-2)

> Documento interno do grupo (fica em `.claude/`, versionado para continuarmos de qualquer computador). É a referência única do projeto: o que a rubrica pede, como o laboratório e o agente são montados, o que vai para o repositório, em que ordem fazemos e quem faz o quê.
> Painel visual: `.claude/painel.html` · Método da Fase 3.1: `.claude/guia_raciocinio_fase31.md`

> **Ideia central:** a nota não depende de quantas vulnerabilidades acharmos nem da autonomia do agente. Depende da qualidade dos testes, da capacidade de **supervisionar** a IA e de **conclusões presas a evidências**. Hipótese refutada com boa evidência é resultado válido.

**Este plano não é um entregável do PDF.** O que vai para a correção são os 5 itens da seção 7 do enunciado (lab reproduzível, código, registros, relatório, vídeo). Tudo que for entregue sai do repositório git (seção 5).

---

## 1. O que a rubrica pede

| Critério | Peso | O que precisa existir para nota cheia | Como comprovamos |
|---|---|---|---|
| Funcionamento e reprodução do laboratório | 15% | Juice Shop + Ollama + Kali + agente sobem **no kit de laboratório** seguindo só o README; restauração leva a um estado conhecido e **verificado** | Integrante que não montou o lab reproduz no kit; reset testado 2× com verificação objetiva; testes de isolamento salvos |
| Desenvolvimento e integração do agente | 20% | ≥ 2 ferramentas (≥ 1 interage com o Juice Shop); ciclo objetivo → proposta → decisão → execução → interpretação; decisões variam com os resultados; limites de escopo **no código e na rede** | Logs em que o turno N cita o resultado do turno N−1; mesmo objetivo rodado 2× com ambiente diferente gerando caminhos diferentes; teste negativo de escopo logado |
| Planejamento e qualidade técnica dos testes | 20% | Análise inicial manual → plano **sem IA** com hipóteses falseáveis, ferramenta justificada por hipótese, evidência que confirma **e** que refuta; depois revisão pelo LLM com tabela aceita/modificada/rejeitada + justificativa técnica; hipóteses novas surgidas nos testes registradas | Commit **e push** do plano antes da revisão (hash e horário no relatório); tabela 3.2; campo `nova_hipotese` no log |
| Evidências e interpretação | 20% | 3 investigações distintas, 6 itens cada; separação entre observado / interpretado pelo modelo / concluído pelo grupo | Toda conclusão cita `investigacao_<id>.jsonl, turno N` (e o arquivo bruto quando houver) |
| Análise crítica da IA | 20% | 7 perguntas da seção 6 respondidas com exemplos do log; ≥ 1 caso concreto de falha (detecção e tratamento); comparação plano do grupo × agente | Métricas por investigação + estudo(s) de caso + tabela de comparação + previsão do grupo × o que aconteceu |
| Documentação e apresentação | 5% | Relatório de 4 a 6 páginas focado em interpretação; vídeo ≤ 10 min com 1 investigação completa (hipótese → conclusão) | Contagem de páginas; roteiro cronometrado; cortes sinalizados |

**Regras do enunciado que não podemos violar**
- Tudo roda **no kit de laboratório** (nada no notebook pessoal, na nuvem ou com LLM externo) e é restrito à instância local do Juice Shop; nada contra serviços externos ou máquinas de outros grupos.
- O Juice Shop é "acessível a partir do Kali" (seção 1) e as ferramentas são as do Kali, como Nmap e curl (seção 2).
- O agente não tem acesso irrestrito ao terminal/SO.
- Sequência fixa de comandos não conta como agente.
- Sugestão do modelo **não** é evidência.
- Planejamento inicial **sem LLM**; só depois a revisão pelo modelo.

---

## 2. Estado do kit e decisões

### 2.1 O que já existe (levantado em 29/10/2026)

O kit é o mesmo do Roteiro 1 (firewall pfSense), montado pelo Grupo 6:

| Item | Valor |
|---|---|
| Acesso do grupo | Wi-Fi WannaCry (172.16.50.x) → VPN OpenVPN do Grupo 6 (túnel 10.8.0.0/24, split tunnel) → LAN 10.0.80.0/24 |
| pfSense | WAN 192.168.20.26 (bloqueia SSH, ICMP e 443; libera 1194/UDP e NAT de 80 e 8000 para o servidor) · LAN 10.0.80.1 |
| Servidor | Ubuntu Server 24.04.5 físico, `aps1lr`, usuário `lr` (grupo `docker`), 10.0.80.3, 15 GB RAM, 20 núcleos, 84 GB livres, relógio em UTC |
| Já instalado | Docker 29.1 + Compose 2.40, nmap 7.94, ffuf 2.1, Python 3.12, `ufw` ativo |
| Sobras do Roteiro 1 | Apache em `*:80`, `*:8000`, `*:8080` (WordPress/Nextcloud), MariaDB em `127.0.0.1:3306`; NAT do pfSense ainda aponta 80/8000 da WAN para o servidor |
| Falta | Ollama, Juice Shop, Kali, agente |

### 2.2 Onde fica o Kali (decidido)

O PDF cita o Kali duas vezes, e o kit não tem uma máquina Kali. Opções avaliadas:

| Opção | Atende "acessível a partir do Kali" | Roda no kit | Isolamento | Veredito |
|---|---|---|---|---|
| Sem Kali, ferramentas via `apt` no Ubuntu | Não, literalmente | Sim | Só o código do wrapper | Arriscado em Lab 15% |
| VM Kali no notebook pela VPN | Sim | **Não** (notebook pessoal) | Depende da VPN | Viola "no kit" |
| **Kali em container no servidor** (`kalilinux/kali-rolling`) | **Sim** | **Sim** | Rede Docker própria + bloqueio de saída | **Escolhida** |

Como fica: o agente (Python no host) executa **todas** as ferramentas dentro do container `kali` (`docker exec kali nmap ...`). O container `kali` e o `juiceshop` ficam numa rede Docker própria (`labnet`); do ponto de vista do Kali, o alvo é `juiceshop:3000`. Isso dá **três camadas de escopo**, cada uma com evidência própria:
1. **Código:** o wrapper só aceita `juiceshop:3000` e flags da allowlist.
2. **Rede Docker:** a `labnet` é `internal` (sem rota para internet, LAN 10.0.80.x e pfSense — testado em 29/10) e uma regra `ufw deny from 172.31.80.0/24` impede que os containers alcancem serviços do próprio servidor pelo gateway da bridge (sem ela, SSH e Apache ficavam alcançáveis — testado).
3. **Perímetro:** o pfSense não tem NAT para a 3000; de fora, o Juice Shop é invisível.

### 2.3 Decisões em aberto

| Decisão | Recomendado | Status |
|---|---|---|
| Integrantes | O relatório do Roteiro 1 lista Lucas Kamikawa e Raphael Barbuti; confirmar se a AF é a mesma dupla | ☐ |
| Data de entrega | — | ☐ ____/____ |
| Uso de IA externa no código/documentos | perguntar **por escrito** ao professor, seguir a resposta; se permitido, declarar no relatório | ☐ |
| Kali em container atende? | incluir na mesma pergunta; a escolha já é defensável sozinha | ☐ |
| Apache/MariaDB do Roteiro 1 durante a AF | **parar** (`systemctl stop`/`disable`) e remover ou desativar o NAT 80/8000 no pfSense: o Juice Shop vira o único serviço web do kit e libera memória. A configuração fica guardada para religar se precisar | ☐ |
| Versão do Juice Shop e do Kali | fixar por **digest** no dia da F1 e anotar no README | ☐ |
| Parâmetros do modelo | temperatura baixa, seed fixa, thinking desligado, `num_ctx` medido | ☐ |
| Fuso dos logs | manter o servidor em UTC e gravar timestamps ISO 8601 com fuso (`...-03:00`), como foi preciso explicar nos logs do pfSense no Roteiro 1 | ☐ |

---

## 3. Arquitetura

### 3.1 Laboratório

```
 Notebook do grupo (Wi-Fi WannaCry)
   │ OpenVPN Grupo 6 (10.8.0.x)
   ▼
 pfSense  WAN 192.168.20.26 ── sem NAT para a 3000 ── LAN 10.0.80.1
   │
   ▼
┌──────────────────────── Ubuntu Server 10.0.80.3 (kit) ───────────────────────┐
│  Ollama qwen3:4b ─ 127.0.0.1:11434                                            │
│  Agente (Python, venv) ── docker exec ──┐                                    │
│                                          ▼                                   │
│   rede Docker "labnet" (internal)  ┌──────────────┐     ┌──────────────────┐ │
│   172.31.80.0/24                   │ kali .20     │────►│ juiceshop .10    │ │
│                                    │ nmap/curl/ffuf│     │ :3000 (digest)   │ │
│                                    └──────────────┘     └──────────────────┘ │
│   nenhuma porta publicada; o host alcança 172.31.80.10 pela bridge           │
│  logs/ (JSONL) · lab/restore.sh · lab/check_env.sh                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Acesso do grupo**
- Terminal: VPN + `ssh lr@10.0.80.3`.
- Navegador para a exploração manual da F2: VPN + `ssh -L 3000:172.31.80.10:3000 lr@10.0.80.3` e abrir `http://localhost:3000` no notebook. O Juice Shop continua rodando só no kit; o túnel apenas exibe a página.
- Ferramentas manuais: `docker exec -it kali bash` (as mesmas que o agente usa).

**Isolamento**
- Nenhuma porta do Juice Shop publicada no host; Ollama em `127.0.0.1:11434` (nunca `OLLAMA_HOST=0.0.0.0`; o Ollama não tem autenticação).
- `labnet` com `internal: true`: o Docker não cria rota de saída, então os containers não alcançam internet, LAN nem pfSense. Não precisa de regra de firewall para isso.
- Única regra com `sudo`, feita pelo grupo uma vez: `sudo ufw insert 1 deny from 172.31.80.0/24`, para os containers não alcançarem SSH/Apache do próprio servidor pelo gateway 172.31.80.1. O `ufw` filtra só conexões novas, então o túnel do navegador e o `docker exec` continuam funcionando.
- Assim o próprio Juice Shop não consegue buscar uma URL externa sugerida pelo agente, e o Kali só enxerga o Juice Shop. O host mantém internet para `apt`, `pip`, `docker pull` e `ollama pull`.
- Ollama v0.40.13 instalado em `~/.local/ollama` (sem sudo) e iniciado por `lab/ollama.sh start` (precisa repetir após reboot; o `check_env.sh` acusa se estiver parado).
- **Testes de isolamento** (saídas em `lab/evidencias/`, vão para o relatório):
  1. Do notebook **sem VPN**: `192.168.20.26:3000` não responde (pfSense).
  2. Do notebook **com VPN**: `10.0.80.3:3000` e `10.0.80.3:11434` recusam conexão (nada publicado / bind em loopback).
  3. De dentro do `kali`: `juiceshop:3000` responde; internet, `10.0.80.1`, `10.0.80.3:22` e o gateway da `labnet` não respondem.
  4. De dentro do `juiceshop`: internet não responde.

**Restauração (`lab/restore.sh`)**
1. `docker compose down` e `docker compose up -d --force-recreate` (só o `juiceshop`; o `kali` não guarda estado da investigação).
2. Esperar HTTP 200 (laço com timeout).
3. Verificação objetiva do estado inicial, impressa pelo script: nenhum desafio resolvido em `/api/Challenges` e um marcador criado antes do reset (ex.: usuário de teste) não existe mais.
4. Quem executa é o grupo, no terminal. O restore **não** é ferramenta do agente.

**Reprodutibilidade:** digests do Juice Shop e do Kali, versões das ferramentas dentro do Kali, versão do Ollama, digest do modelo, quantização, `num_ctx`, `temperature`, `seed`, thinking e tempo médio por resposta, tudo no README.

### 3.2 Agente

Python com chamadas diretas a `/api/chat` do Ollama, sem framework pesado (os dois integrantes conseguem explicar o loop). Saída do modelo em JSON com schema fixo (`format` com JSON Schema), validada antes de qualquer execução.

```
Objetivo da investigação (só o objetivo, sem a hipótese nem a estratégia do grupo)
   │
   ▼
LLM: {ferramenta, parâmetros, justificativa} ◄────────────────────────────┐
   │   JSON inválido → 1 nova tentativa com o erro (logada)              │
   ▼                                                                     │
Humano: [A]utorizar / [M]odificar / [R]ejeitar / [F]inalizar (+ motivo)   │
   │            └─ M/R: decisão e motivo voltam ao modelo ───────────────┤
   ▼                                                                     │
Wrapper valida (alvo e flags da allowlist) ──► docker exec kali <argv>   │
   │   saída completa → logs/raw/ ; resumo truncado → modelo             │
   ▼                                                                     │
LLM interpreta + atualiza "fatos observados" ────────────────────────────┘
   │
Grupo registra a decisão após o resultado (e nova hipótese, se houver)
   │
Uma linha por turno em logs/investigacao_<id>.jsonl, gravada na hora
```

**Ferramentas expostas ao modelo** (≥ 2, ≥ 1 no Juice Shop; todas executadas no container `kali`)

| Ferramenta | Por baixo | Limites no código |
|---|---|---|
| `http_request(method, path, headers, body)` | `curl` | Alvo fixo `http://juiceshop:3000`; o modelo escolhe só path, método, headers e corpo; sem `-L` para fora do alvo; timeout; tamanho máximo |
| `nmap_scan(flags)` | `nmap` | Alvo fixo `juiceshop`, porta 3000; flags de uma allowlist (ex.: `-sT`, `-sV`, `-Pn`), sem `--script` arbitrário |
| `dir_enum(wordlist)` (opcional) | `ffuf` | Wordlist pequena pré-definida; rate limit; filtro por tamanho de resposta (o Juice Shop é SPA e responde 200 com o `index.html` para quase qualquer rota) |
| `decode_jwt(token)` (opcional) | Python local | Sem rede |

**Regras de segurança**
- O wrapper monta o `argv` a partir de parâmetros validados e chama `docker exec` sem shell (`subprocess.run([...])`, nunca `shell=True`); não há shell livre para o modelo.
- Pedido fora da allowlist → recusa + registro (`fora_escopo`). Teste negativo documentado. Mesmo que o código falhasse, a rede da camada 2 bloquearia.
- Limite de turnos por investigação (ex.: 15) e timeout por ferramenta.
- URLs externas em parâmetros são rejeitadas pelo grupo e marcadas `fora_escopo`.

**Cuidados com o qwen3:4b**
- Thinking desligado (`"think": false`) ou bloco `<think>` separado antes de validar; a resposta bruta é sempre guardada.
- Contexto curto: saída ao modelo truncada (ex.: 3–4 mil caracteres) e lista curta de "fatos observados" reenviada a cada turno.
- Depois de Modificar/Rejeitar, o próximo prompt contém a decisão e o motivo; senão o modelo repete a proposta.
- Prompt de sistema versionado em `agent/prompts/`, com hash no log.

---

## 4. Formato do log (JSONL, uma linha por turno)

Cobre os 6 itens da seção 5 do PDF e o que a análise crítica precisa:

```json
{
  "investigacao": "I2",
  "sessao": "I2-2026-11-05T14:02-03:00",
  "turno": 4,
  "timestamp": "2026-11-05T14:09:31-03:00",
  "objetivo": "...",
  "config": {"modelo": "qwen3:4b", "digest": "...", "temperature": 0.2, "seed": 42, "prompt_sha256": "...", "juiceshop_digest": "...", "kali_digest": "..."},
  "resposta_bruta_modelo": "...",
  "json_valido": true,
  "tentativas": 1,
  "justificativa_modelo": "...",
  "ferramenta_proposta": "http_request",
  "parametros_propostos": {"method": "GET", "path": "/..."},
  "decisao_humana": "AUTORIZADO | MODIFICADO | REJEITADO | FINALIZADO",
  "motivo_decisao": "...",
  "parametros_executados": {},
  "comando_executado": ["docker", "exec", "kali", "curl", "..."],
  "bloqueio_escopo": null,
  "saida_resumo": "...",
  "saida_arquivo": "logs/raw/I2_turno4.txt",
  "saida_sha256": "...",
  "duracao_ms": {"modelo": 0, "ferramenta": 0},
  "interpretacao_modelo": "...",
  "fatos_observados": ["..."],
  "decisao_grupo_pos_resultado": "...",
  "nova_hipotese": null,
  "tags": []
}
```
- Turno REJEITADO: campos de execução e interpretação ficam `null`; o motivo é registrado e enviado ao modelo.
- Primeira linha de cada investigação: registro `restore` (horário + saída da verificação).
- Tags marcadas na hora: `falha_ia`, `alucinacao`, `json_invalido`, `repeticao`, `fora_escopo`, `interpretacao_errada`, `boa_sugestao`.
- Logs nunca editados à mão. `agent/summarize_logs.py` gera as métricas (A/M/R/F, falhas por tipo, repetições, tempo por turno) e o `.md` legível de cada investigação.

---

## 5. Estrutura do repositório git (o que é entregue)

```
├── README.md                     # acesso ao kit, subir o lab, rodar o agente, restore
├── lab/
│   ├── docker-compose.yml        # juiceshop + kali na rede labnet (digests fixos)
│   ├── kali/Dockerfile           # kali-rolling + nmap, curl, ffuf, wordlist pequena
│   ├── install.sh                # Ollama (sem sudo) + modelo + build/up dos containers
│   ├── ollama.sh                 # start/stop/status do Ollama em loopback
│   ├── restore.sh                # recria o juiceshop e verifica o estado inicial
│   ├── check_env.sh              # alvo, Ollama, Kali, versões e os 4 testes de isolamento
│   └── evidencias/               # saídas dos testes de isolamento e de restore
├── agent/
│   ├── agent.py                  # loop A/M/R/F
│   ├── llm.py                    # cliente Ollama + validação do JSON
│   ├── scope.py                  # allowlist de alvo e flags
│   ├── tools/                    # http_request, nmap_scan, dir_enum, decode_jwt
│   ├── logger.py
│   ├── summarize_logs.py
│   ├── config.example.yaml
│   ├── prompts/                  # sistema.md, revisao_plano.md (versionados)
│   ├── tests/                    # testes da allowlist e da validação
│   └── requirements.txt
├── planejamento/
│   ├── observacoes_iniciais.md   # análise manual datada (grupo, sem IA)
│   ├── plano_testes_grupo.md     # Fase 3.1 (grupo, sem IA) — commit + push antes da 3.2
│   └── revisao_llm.md            # Fase 3.2: resposta bruta + tabela A/M/R
├── logs/
│   ├── P0_piloto.jsonl
│   ├── investigacao_I1.jsonl … I3.jsonl
│   └── raw/
├── investigacoes/
│   └── I1.md  I2.md  I3.md       # os 6 itens de cada investigação
├── relatorio/relatorio.pdf       # 4 a 6 páginas
└── video/LINK.md
```

- `.claude/` é versionado (contexto, plano, guia e painel, para continuar de outro computador). `rascunhos/` fica fora (`.git/info/exclude`). `.gitignore` cobre `agent/config.toml`, `__pycache__/`, `.venv/` e `.claude/settings.local.json`.
- Commits só em nome dos integrantes, mensagens em português.
- O repositório fica no notebook (com remoto no GitHub) e é copiado para `~/af` no servidor via SSH. O remoto precisa existir **antes da F4**: o horário do push é a prova de que o plano veio antes da revisão.

---

## 6. Fases

```
F0 Organização + decisões ─► F1 Laboratório ─► F2 Análise manual + Plano 3.1 (sem IA) ─► [commit + push]
                                   │                                                         │
                                   └──► F3 Agente (teste de fumaça com objetivo neutro) ─────┤
                                                                                             ▼
                                                                        F4 Revisão do plano pelo LLM (3.2)
                                                                                             ▼
                                                                 F5 Piloto P0 → Investigações I1, I2, I3
                                                                                             ▼
                                                                        F6 Análise crítica (a partir dos logs)
                                                                                             ▼
                                                                        F7 Relatório + vídeo ─► F8 Revisão final
```

> **Cuidado com a ordem:** enquanto o plano 3.1 não estiver no remoto, o grupo **não** vê propostas do agente sobre os temas das investigações. O teste do agente na F3 usa um objetivo neutro (ex.: "verificar se o serviço responde e qual versão roda"). O piloto de calibração (P0) só acontece depois do push.

### F0 — Organização
- Criar o remoto, fechar a seção 2.3, mandar a pergunta ao professor.
- **Pronto quando:** seção 2.3 preenchida e data de entrega no cronograma.

### F1 — Laboratório (15%)
- Implementar a seção 3.1: Ollama, compose com `juiceshop` + `kali`, `firewall.sh`, `restore.sh`, `check_env.sh`, README.
- **Pronto quando:** o outro integrante reproduz tudo **no kit** só com o README; reset testado 2× com a verificação salva; os 4 testes de isolamento salvos.

### F2 — Análise inicial manual + Plano 3.1 (sem IA)
- Explorar a aplicação manualmente (navegador via túnel SSH, DevTools, ferramentas do `kali` vistas em aula) e registrar observações datadas em `planejamento/observacoes_iniciais.md`.
- Preencher `planejamento/plano_testes_grupo.md` com o template do guia. Para cada investigação: aspecto e por quê, hipóteses falseáveis, ferramenta por hipótese, evidência que confirma e que refuta, ligação com a disciplina, previsão sobre a IA.
- Três investigações distintas, seguindo os temas sugeridos pelo PDF: I1 reconhecimento/enumeração, I2 autenticação/autorização, I3 entradas/requisições/acesso a recursos.
- **Pronto quando:** plano commitado **e enviado ao remoto**. Hash e horário anotados.

### F3 — Agente supervisionado (20%)
- Implementar a seção 3.2 e o log da seção 4.
- Testes automáticos da allowlist (alvo externo, `10.0.80.1`, `host.docker.internal`, porta 22/11434, flag proibida, redirect) e da validação do JSON.
- **Pronto quando:** teste de fumaça com objetivo neutro roda de ponta a ponta; o log reconstrói cada turno sem olhar o terminal; teste negativo de escopo aparece no log.

### F4 — Revisão do plano pelo LLM (3.2)
- Enviar o plano ao modelo com `agent/prompts/revisao_plano.md`, pela mesma integração (chamada fica em log).
- Tabela em `planejamento/revisao_llm.md`: `# | Sugestão do modelo | Aceita/Modificada/Rejeitada | Justificativa técnica`. Sugestões erradas ou genéricas também entram.
- O que for aceito vira um **novo commit** do plano; o original fica intacto.
- **Pronto quando:** tabela completa, resposta bruta arquivada, commit da revisão posterior ao do 3.1.

### F5 — Investigações (20%)
**Piloto P0** (descartável, depois do push): calibrar prompt e wrappers; registrar o que mudou para a rodada oficial.

Para cada uma das 3:
1. `restore.sh` + verificação, registrados no log.
2. Dar ao agente **só o objetivo** (sem hipótese nem estratégia do grupo), para que a contribuição do agente seja dele.
3. Decidir cada proposta e **sempre** justificar Modificar/Rejeitar.
4. Após cada resultado, registrar a decisão do grupo; hipóteses novas em `nova_hipotese`.
5. Confirmar qualquer afirmação do modelo com evidência independente.
6. Encerrar com CONFIRMADA / REFUTADA / INCONCLUSIVA + limitações; preencher `investigacoes/Ix.md` com os 6 itens do PDF.
- Em ao menos 1 investigação, rodar **o mesmo objetivo duas vezes** com uma mudança controlada no ambiente. Com seed e temperatura fixas, a divergência só pode vir dos resultados das ferramentas.
- **Pronto quando:** os 6 itens preenchidos nas 3, cada afirmação citando `investigacao_<id>.jsonl, turno N`.

### F6 — Análise crítica (20%)
- Métricas por investigação via `summarize_logs.py`.
- 7 perguntas do PDF, cada uma com exemplo de log.
- Estudo(s) de caso de falha: o que o modelo fez → como percebemos → o que fizemos → o que isso diz sobre o modelo ou a integração.
- Comparações: plano do grupo × agente (igual / diferente / novo + resultado) e previsão do grupo × realidade.
- Limitações do modelo e da integração, separadas. Taxa alta de Modificar é dita com honestidade.

### F7 — Relatório (4 a 6 páginas) e vídeo (≤ 10 min)
- Páginas: introdução e escopo/ética 0,25 · arquitetura 0,75 · estratégia (plano + tabela 3.2) 1 · investigações 2 · análise crítica 1,75 · conclusão 0,25.
- Na arquitetura, aproveitar o Roteiro 1: pfSense + VPN como perímetro, e as três camadas de escopo do agente.
- Sem prints sem análise; sem instalação (fica no README). Sempre separar observado / interpretado pelo modelo / concluído pelo grupo. Citar hash e horário do push do plano.
- Vídeo: roteiro no painel; os dois integrantes falam. Cortes de espera da inferência sinalizados na tela.

### F8 — Revisão final
- Checklist do painel 100%; README reproduzido no kit; logs e `raw/` no repositório; páginas e duração conferidas; declaração de uso de IA conforme resposta do professor.

---

## 7. Passo a passo para terminar o projeto

Legenda: **G** = só o grupo pode fazer · **R** = preparado no repositório/servidor e revisado pelo grupo antes do commit.

| # | Passo | Quem | Depende de | O que sai |
|---|---|---|---|---|
| 1 | Fechar a seção 2.3 (dupla, data, Apache) e mandar ao professor a pergunta sobre IA externa e Kali em container | G | — | Decisões fechadas |
| 2 | ~~Acesso SSH ao kit~~ (feito em 29/10: VPN + chave `af_kit`) | — | — | Acesso |
| 3 | ~~Remoto no GitHub~~ (feito em 04/11: github.com/lucaskmk/IA-Testes-de-seguranca-ofensivos, 4 commits enviados) | G | — | Prova de data disponível |
| 4 | ~~Ollama~~ (feito em 29/10: v0.40.13 no espaço do usuário, sem sudo) | — | — | Ollama no ar |
| 5 | ~~Escrever `lab/` e o README; baixar imagens e o modelo~~ (feito em 29/10) | R | 4 | Scripts do lab |
| 6 | ~~Regra do `ufw`~~ (feito em 04/11: o `ufw` estava desativado; ativado com `deny from 172.31.80.0/24` + `allow OpenSSH`. Efeito colateral: Apache do Roteiro 1 fechado para a rede) | G | 5 | Isolamento completo |
| 7 | ~~Restore 2×, testes de isolamento 1 a 4, `check_env` com 0 falhas~~ (feito; `lab/evidencias/`) | R + G | 6 | `lab/evidencias/` |
| 8 | Explorar o Juice Shop manualmente e escrever observações + plano 3.1 **sem IA**; commit + push | G | 7 | Plano 3.1 no remoto |
| 9 | ~~Agente, testes (25 + 14 casos de escopo), `summarize_logs.py`, `revisar_plano.py`~~ (feito em 29/10) | R | 5 | `agent/` |
| 10 | ~~Teste de fumaça com objetivo neutro~~ (feito em 29/10: `logs/investigacao_T0_fumaca.jsonl`, ~35–42 s por chamada) | R | 7, 9 | Agente validado |
| 11 | Rodar a revisão 3.2 e preencher a tabela A/M/R com as justificativas | G (prompt: R) | 8, 10 | `revisao_llm.md` |
| 12 | Piloto P0; ajustar prompt/wrappers; registrar mudanças | G (ajustes: R) | 11 | Versão oficial do agente |
| 13 | Conduzir I1, I2, I3 (cada integrante conduz pelo menos uma) + execução dupla | G | 12 | Logs JSONL |
| 14 | Gerar métricas e tabelas a partir dos logs | R | 13 | Insumos da F6 |
| 15 | Escrever os 6 itens de cada investigação e a análise crítica | G (revisão de forma: R) | 14 | `investigacoes/`, rascunho do relatório |
| 16 | Fechar o relatório (4–6 p.) e gravar o vídeo | G | 15 | Entregáveis 4 e 5 |
| 17 | Revisão final pelo checklist | G + R | 16 | Entrega |

**Modo de trabalho com acesso SSH ao kit**
- Acesso: VPN do Grupo 6 conectada pelo grupo + `ssh kit` (chave dedicada `~/.ssh/af_kit`), sem senha e **sem sudo**. Comandos com `sudo` são rodados pelo grupo.
- Por SSH: escrever e implantar `lab/` e `agent/`, baixar imagens e modelo, rodar restore, testes de escopo e de isolamento e o teste de fumaça com objetivo neutro.
- **Nunca** por SSH: explorar o Juice Shop (F2), escrever o plano 3.1, decidir A/M/R/F nas investigações, preencher justificativas da tabela 3.2. Essas partes são a "intervenção humana" que o PDF avalia.

Pontos de bloqueio: sem o passo 4 não há modelo; sem o 8 no remoto não se roda nada do agente sobre os temas das investigações; sem o 13 não existe relatório.

---

## 8. Cronograma (data de entrega: ____/____)

| Semana | Passos | Entregável interno |
|---|---|---|
| 1 | 1–7, início de 8 e 9 | Decisões fechadas; lab reproduzível e isolado |
| 2 | 8 (push), 9, 10 | Plano 3.1 no remoto; agente validado |
| 3 | 11–13 | Tabela 3.2; 3 investigações com logs |
| 4 | 14–17 | Análise crítica; relatório; vídeo |

Pelo menos **30% do tempo para os passos 13–16** (somam 60% da nota). Com 20 núcleos e sem GPU, medir no passo 10 o tempo por turno e replanejar.

---

## 9. Papéis (dupla)

| Integrante | Frente principal | Também conduz e precisa saber explicar |
|---|---|---|
| A | Laboratório (README, firewall, restore, evidências de isolamento) + relatório | Uma investigação inteira; o loop do agente |
| B | Agente (prompt, allowlist, log, métricas) + vídeo | Uma investigação inteira; a topologia e as três camadas de escopo |

A terceira investigação é conduzida em conjunto. Os dois precisam conseguir explicar a arquitetura e as decisões de implementação (exigência do PDF, seção 2).

---

## 10. Riscos

| Risco | Impacto | Prevenção |
|---|---|---|
| Professor não aceita Kali em container | Desconto em Lab 15% | Perguntar cedo; o agente só depende do nome do alvo, então trocar é barato |
| Apache/NAT do Roteiro 1 ativos durante a AF | Mais de um serviço web no kit; confusão sobre o alvo | Parar Apache/MariaDB e o NAT 80/8000 (decisão 2.3); allowlist só aceita `juiceshop:3000` |
| Porta publicada por engano | Juice Shop/Ollama visíveis na LAN e pela VPN | Compose sem `ports`; Ollama em loopback; teste de isolamento 2 |
| Ollama parado após reboot (instalação sem systemd) | Agente sem modelo | `lab/ollama.sh start`; `check_env.sh` acusa |
| Juice Shop busca URL sugerida pelo agente | Saída de escopo pelo próprio alvo | `labnet` sem saída; URLs externas rejeitadas |
| VPN cai durante uma investigação | Sessão do agente interrompida | Rodar o agente dentro de `tmux` no servidor; log gravado a cada turno |
| Enumeração em SPA devolve 200 em tudo | Resultado inútil, conclusão errada | Filtro por tamanho; registrar se o modelo errar mesmo assim |
| JSON quebrado / texto de "thinking" | Loop trava | Validação + nova tentativa; logar (vira estudo de caso) |
| Modelo não recebe o motivo da rejeição | Repete a proposta | Motivo reenviado no turno seguinte |
| Saída grande estoura o contexto | Modelo perde o fio | Truncamento + fatos observados |
| Modelo "lembra" soluções públicas do Juice Shop | Mede memória, não raciocínio | Marcar quando a proposta não deriva do resultado anterior |
| Grupo vê propostas do agente antes do plano 3.1 | Plano contaminado, comparação inválida | Teste de fumaça com objetivo neutro; P0 só depois do push |
| Agente recebe a estratégia do grupo | Comparação grupo × agente perde valor | Passar só o objetivo |
| Inferência lenta em CPU | Atraso nas investigações e no vídeo | Medir cedo; thinking desligado; `num_ctx` menor |
| Horários confusos entre UTC e Brasília | Evidência difícil de cruzar | Timestamps ISO 8601 com fuso |
| Relatório passa de 6 páginas | Desconto | Orçamento por seção |
| Reset não volta ao estado inicial | Experimentos não reproduzíveis | Verificação objetiva, testada 2× |
| Uso de IA externa não declarado | Integridade acadêmica | Perguntar ao professor e seguir a resposta |

---

## 11. Convenções

- IDs: `P0` (piloto), `I1`, `I2`, `I3`.
- Logs: `logs/investigacao_<id>.jsonl` · saídas: `logs/raw/<id>_turno<N>.txt`.
- Citação: `investigacao_I2.jsonl, turno 5`.
- Decisões: `AUTORIZADO` · `MODIFICADO` · `REJEITADO` · `FINALIZADO`.
- Conclusões: `CONFIRMADA` · `REFUTADA` · `INCONCLUSIVA`.
- Plano: `planejamento/plano_testes_grupo.md` · revisão: `planejamento/revisao_llm.md`.
- Timestamps: ISO 8601 com fuso (`-03:00`).
- Rascunhos (relatório, análise): `rascunhos/`, fora do git via `.git/info/exclude`; entram no repositório só depois de revisados pela dupla.
