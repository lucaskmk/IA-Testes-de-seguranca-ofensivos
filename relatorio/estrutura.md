# Estrutura do relatório técnico (4 a 6 páginas)

Orçamento de páginas e o que cada seção precisa trazer. Instalação fica no README.

| Seção | Páginas | Conteúdo | Fontes |
|---|---|---|---|
| 1. Introdução, escopo e ética | 0,25 | Objetivo; alvo único; isolamento | `lab/evidencias/` |
| 2. Arquitetura do laboratório e do agente | 0,75 | Diagrama; três camadas de escopo; ciclo A/M/R/F; formato do log; versões fixadas | README, `agent/`, `logs/teste_escopo.jsonl` |
| 3. Estratégia de testes | 1 | Plano do grupo (commit e horário do push); tabela da revisão 3.2 com aceitas, modificadas e rejeitadas | `planejamento/` |
| 4. Resultados das investigações | 2 | Os 6 itens de cada investigação, resumidos; cada afirmação com `investigacao_<id>.jsonl, turno N` | `investigacoes/`, `logs/` |
| 5. Análise crítica da IA | 1,75 | Métricas; respostas às 7 perguntas com exemplos de log; estudo de caso de falha; comparação plano × agente; previsão × realidade; limitações do modelo e da integração, separadas | `relatorio/metricas.md`, `logs/` |
| 6. Conclusão e limitações | 0,25 | O que a IA ajudou, onde falhou, onde a intervenção humana foi indispensável | — |

Regras: nenhum print sem análise; sugestão do modelo não é evidência; sempre separar observado, interpretado pelo modelo e concluído pelo grupo.
