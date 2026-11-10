# Índice da entrega — AF Tecnologias Hackers (Grupo 6)

Ponto de entrada único. Cada critério da rubrica aponta para onde está o entregável e a evidência. Resultado das 3 investigações: **todas CONFIRMADA**.

## Mapa da rubrica → onde está

| Critério (peso) | Onde está | Resumo |
|---|---|---|
| **Lab reproduzível (15%)** | `README.md`, `lab/`, `lab/evidencias/` | Juice Shop + Kali em Docker isolado, Ollama local, restore verificado, isolamento em 3 camadas com evidência |
| **Agente supervisionado (20%)** | `agent/`, `agent/tests/`, `logs/teste_escopo.jsonl` | 4 ferramentas, trava de escopo (14/14 no teste negativo), loop A/M/R/F, log JSONL por turno, 33 testes de unidade |
| **Planejamento (20%)** | `planejamento/` | Plano do grupo (3 hipóteses falseáveis), commit antes da revisão; revisão 3.2 pelo modelo com tabela aceita/modificada/rejeitada |
| **Evidências (20%)** | `investigacoes/I1.md`, `I2.md`, `I3.md` + `logs/` | 6 itens por investigação; cada conclusão cita `logs/investigacao_<id>.jsonl, turno N`; saídas brutas com SHA-256 conferido |
| **Análise crítica (20%)** | `relatorio/analise_critica.md` | 7 perguntas com exemplos de log, 3 casos de falha, comparação plano × agente, limitações do modelo e da integração |
| **Documentação e vídeo (5%)** | `relatorio/relatorio.md`, `video/roteiro_video.md` | Relatório de 4–6 páginas; roteiro cronometrado do vídeo (demo = I2) |
| **Extra — comparar modelos locais** | `agent/comparar_modelos.py`, `relatorio/comparacao_modelos.md` | Reenvia uma decisão registrada a vários modelos do Ollama; 3 modelos (qwen3:4b, llama3.2:3b, gemma2:2b) — nenhum conduz sozinho |

## Resultado de cada investigação

- **I1 — Reconhecimento (CONFIRMADA):** o `main.js` declara 45 rotas, incluindo `administration`, `accounting`, `data-export` não linkadas no menu. O modelo não as extraiu; a supervisão sim. → `investigacoes/I1.md`
- **I2 — Autorização (CONFIRMADA):** a conta comum lê o registro do admin via `GET /api/Users/1` (IDOR). JWT RS256 refuta "JWT fraco", mas expõe hash MD5 da senha e `totpSecret`. → `investigacoes/I2.md`
- **I3 — Entrada (CONFIRMADA):** `q=apple'` → `500 SQLITE_ERROR` (SQL injection). A trava de escopo bloqueou o payload de tautologia do modelo. → `investigacoes/I3.md`

## Números (de `relatorio/metricas.md`)

13 turnos nas 3 investigações. **7 modificados, 1 rejeitado, 1 bloqueio de escopo** (supervisão em >60% dos turnos). 0 JSON inválido. As duas falhas só se confirmaram por intervenção humana.

## Estrutura do repositório

```
README.md            Como montar e reproduzir o laboratório (começar aqui para rodar)
INDICE.md            Este índice
lab/                 docker-compose, restore, check_env, install, ollama; evidencias/
agent/               agent.py, scope.py, tools.py, llm.py, logger.py, config, prompts/, tests/
planejamento/        observacoes_iniciais.md, plano_testes_grupo.md, revisao_llm.md
investigacoes/       I1.md, I2.md, I3.md (os 6 itens de cada)
logs/                investigacao_*.jsonl, modelo_*.jsonl, raw/ (saídas com hash)
relatorio/           relatorio.md, analise_critica.md, metricas.md
video/               roteiro_video.md
.claude/             contexto e painel (uso interno do grupo)
```

## Como reproduzir (resumo; detalhe no README)

1. Conectar a VPN do grupo e `ssh` no servidor do kit.
2. `git clone` do repositório e `bash lab/install.sh`.
3. `sudo ufw insert 1 deny from 172.31.80.0/24` (uma vez).
4. `bash lab/check_env.sh` → 0 falhas.
5. Rodar uma investigação: `python3 agent/agent.py --id I1 --restore --objetivo "..."`.

## O que ainda falta (dupla)

- [ ] Revisar e assumir os logs, as decisões e os textos (relatório e análise na voz de vocês).
- [ ] Gravar o vídeo conduzindo vocês mesmos (roteiro em `video/`).
- [ ] Declarar o uso de IA no relatório (marcador na seção 1).
- [ ] Raphael reproduzir o `README.md` no kit (fecha os 15% do lab).
- [ ] Preencher a previsão sobre a IA de I2 e I3 no `plano_testes_grupo.md` (opcional; a de I1 está feita).
