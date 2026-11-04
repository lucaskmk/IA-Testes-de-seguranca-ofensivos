# Contexto do projeto

Avaliação Final de **Tecnologias Hackers** (Insper 2026.2, prof. Rodolfo Avelino): testes de segurança ofensivos com apoio de IA. Dupla: Lucas Kamikawa e Raphael Barbuti (Grupo 6). Repositório: https://github.com/lucaskmk/IA-Testes-de-seguranca-ofensivos

Construímos um **agente supervisionado (human-in-the-loop)** que integra um LLM local (`qwen3:4b` via Ollama) a um conjunto limitado de ferramentas do Kali para investigar uma instância **local** do OWASP Juice Shop. A nota não depende de quantas falhas acharmos: o foco é registrar com evidências onde a IA ajuda, onde falha e quando a intervenção humana é necessária.

Arquivos de referência nesta pasta:
- `.claude/plano_projeto.md`: plano completo (rubrica, arquitetura, log, estrutura do repositório, fases, passo a passo, riscos)
- `.claude/guia_raciocinio_fase31.md`: método e roteiro prático da Fase 3.1 (só método, sem hipóteses)
- `.claude/painel.html`: painel de status (Agora, Caminho, O que foi feito, Nossas escolhas, checklist). Abre direto no navegador. Também publicado como artifact privado na conta do Lucas: https://claude.ai/artifact/VTisN6z8Vx3zXvskX6ph6N (republicar a partir deste arquivo com a mesma URL)

## Rubrica

| Critério | Peso |
|---|---|
| Funcionamento e reprodução do laboratório | 15% |
| Desenvolvimento e integração do agente supervisionado | 20% |
| Planejamento e qualidade técnica dos testes | 20% |
| Qualidade das evidências e interpretação dos resultados | 20% |
| Análise crítica da contribuição da IA | 20% |
| Documentação e apresentação | 5% |

Exigências do enunciado que guiam tudo: tudo roda **no kit**; Juice Shop "acessível a partir do Kali"; agente com ≥ 2 ferramentas (≥ 1 no Juice Shop) e sem shell irrestrito; decisões que variam com os resultados (não sequência fixa); plano inicial **sem LLM**, depois revisão pelo LLM com tabela aceita/modificada/rejeitada; 3 investigações distintas com 6 itens cada (hipótese, estratégia do grupo, contribuição do agente, execução, intervenção humana, conclusão); log com ação proposta, ferramenta/parâmetros, decisão, resultado, interpretação do modelo e decisão do grupo após o resultado; análise crítica com as 7 perguntas da seção 6, ≥ 1 falha concreta e comparação plano × agente; relatório de 4 a 6 páginas; vídeo ≤ 10 min com uma investigação completa.

## Regras fixas

- **Fase 3.1 (planejamento inicial) é escrita pela dupla, sem IA.** Não redigir hipóteses, estratégias nem evidências esperadas dessa fase, nem como rascunho; apenas método, template em branco ou revisão de forma depois que a dupla escrever. A revisão pelo LLM (Fase 3.2) só acontece depois do commit **e push** do plano.
- **Decisões das investigações são da dupla.** Autorizar/modificar/rejeitar/finalizar, justificativas e "decisão após o resultado" vêm da dupla; se for pelo chat, digitar no agente exatamente o que a dupla escreveu.
- **Nenhuma proposta do agente sobre os temas antes do push do plano 3.1.** Testes do agente antes disso só com objetivo neutro.
- **O agente recebe só o objetivo**, nunca a hipótese nem a estratégia do grupo.
- **Escopo:** apenas `juiceshop:3000` na rede `labnet`. Nada contra serviços externos, o pfSense, a LAN ou máquinas de outros grupos.
- **Evidência:** sugestão do modelo não é evidência. Toda conclusão cita `logs/investigacao_<id>.jsonl, turno N`. Logs nunca são editados à mão.
- **Reprodutibilidade:** imagens por digest; digest do modelo, temperatura (0,2), seed (42) e hash do prompt ficam em todo log.
- **Segurança do servidor:** configurações com `sudo` (firewall, pacotes) são feitas pela dupla; o Claude não usa sudo nem digita senhas.

## Escrita e commits

- Todo texto em português, na voz da dupla ("nós"), sem mencionar IA como autora.
- Commits apenas em nome do autor do repositório (LKenji / lucaskmk), **sem** `Co-Authored-By` nem rodapés de ferramenta.
- `.claude/` é versionado (contexto para continuar de outro computador), exceto `.claude/settings.local.json`.
- Rascunhos de plano, análise e relatório ficam em `rascunhos/` (excluído via `.git/info/exclude`, só local): mostrar à dupla; entram no repositório só depois de revisados e assumidos por ela. Os rascunhos atuais (seção de arquitetura do relatório e esqueleto da análise crítica) estão só no notebook do Lucas.
- `.gitattributes` mantém `logs/**` e `lab/evidencias/**` byte a byte (os logs guardam SHA-256 das saídas).

## Laboratório

```
Notebook (Wi-Fi WannaCry 172.16.50.x) ── OpenVPN do Grupo 6 (10.8.0.0/24, split tunnel)
  └► pfSense (WAN 192.168.20.26, LAN 10.0.80.1) ── montado no Roteiro 1
       └► Ubuntu Server 24.04 físico "aps1lr", usuário lr, 10.0.80.3 (15 GB RAM, 20 núcleos, sem GPU)
            ├─ Ollama v0.40.13 em ~/.local/ollama, 127.0.0.1:11434, qwen3:4b (digest 359d7dd4…)
            ├─ repositório em ~/af (cópia; o agente roda daqui)
            └─ rede Docker "labnet" (internal, 172.31.80.0/24)
                 ├─ juiceshop 172.31.80.10:3000  bkimminich/juice-shop:v20.3.0@sha256:cea5a4af…
                 └─ kali      172.31.80.20       af-kali:2026.10 (nmap, curl, ffuf, dirb)
```

- Escopo em três camadas: allowlist no código (`agent/scope.py`), rede (`labnet` interna + `ufw deny from 172.31.80.0/24` + `allow OpenSSH`, ativado em 04/11) e perímetro (pfSense sem NAT para o laboratório; acesso só pela VPN).
- Depois de reiniciar o servidor: os containers voltam sozinhos; o Ollama não: `bash lab/ollama.sh start`.
- Antes de cada investigação: `bash lab/check_env.sh` (precisa dar 0 falhas) e o agente com `--restore`.
- O Apache do Roteiro 1 (WordPress/Nextcloud) continua instalado, mas fechado pelo `ufw`.

### Acessar o kit a partir de outro computador

1. **VPN:** instalar o cliente OpenVPN e importar o perfil de um usuário da VPN do Grupo 6. O Roteiro 1 criou `vpnuser` e `vpnuser2`; o instalador/perfil sai do pfSense em VPN > OpenVPN > Client Export. Conectar a partir do Wi-Fi WannaCry.
2. **SSH com chave própria** (não copiar a chave de outro computador):
   ```
   ssh-keygen -t ed25519 -f ~/.ssh/af_kit -N ""
   ```
   No PowerShell, com a VPN ligada (pede a senha do `lr` uma vez):
   ```
   Get-Content $env:USERPROFILE\.ssh\af_kit.pub | ssh lr@10.0.80.3 "cat >> ~/.ssh/authorized_keys"
   ```
   E no `~/.ssh/config`:
   ```
   Host kit
       HostName 10.0.80.3
       User lr
       IdentityFile ~/.ssh/af_kit
       IdentitiesOnly yes
   ```
3. **Navegador no Juice Shop:** `ssh -L 3000:172.31.80.10:3000 kit` e abrir `http://localhost:3000`.
4. **Sincronizar o código com o servidor:** o repositório local é a fonte. Preferência: commit + push no notebook e `git pull` em `~/af` (o `revisar_plano.py` exige um clone git com o plano no remoto, e o log grava o commit). Alternativa para testes rápidos: `tar czf - agent lab planejamento | ssh kit 'cd ~/af && tar xzf -'` (normalizar CRLF com `sed -i 's/\r$//'` nos `.sh`/`.py`); o log então mostra `agent_com_alteracoes_nao_commitadas: true`, e o hash dos arquivos (`codigo.sha256_conjunto`) identifica o código. Logs gerados no servidor voltam com `ssh kit 'cd ~/af && tar czf - logs lab/evidencias' | tar xzf -` e são commitados e enviados logo após cada investigação.

## Estado em 04/11/2026

Feito (com evidência no repositório):
- Laboratório completo e isolado: restore 2× (`lab/evidencias/restore_*`), `check_env` com 0 falhas, testes de isolamento com e sem VPN.
- Agente completo: 4 ferramentas (`http_request`, `nmap_scan`, `dir_enum`, `decode_jwt`), loop A/M/R/F com justificativa obrigatória, JSON com schema e nova tentativa, log JSONL por turno + chamadas ao modelo + saídas brutas com SHA-256, `summarize_logs.py`, `revisar_plano.py`, `teste_escopo.py` (14/14), 25 testes de unidade, teste de fumaça `T0_fumaca` (28 a 42 s por chamada; o modelo ignorou o limite de "no máximo uma ação", candidato a exemplo de limitação).
- Modelos em branco: `planejamento/observacoes_iniciais.md`, `planejamento/plano_testes_grupo.md`, `investigacoes/I1-3.md`, `relatorio/estrutura.md`.

Próximo passo (bloqueia o resto): **Fase 3.1 pela dupla, sem IA** (roteiro na seção 8 do guia), com commit e push. Depois: `python3 agent/revisar_plano.py` (Fase 3.2; a dupla preenche a tabela) → piloto P0 → I1, I2, I3 (+ execução dupla do mesmo objetivo) → `summarize_logs.py` → 6 itens e análise crítica (dupla) → relatório → vídeo → checklist final.

Pendências da dupla: data de entrega; pergunta por escrito ao professor sobre uso de IA externa e Kali em container; decisão definitiva sobre o Apache do Roteiro 1; README reproduzido pelo Raphael no kit.
