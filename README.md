# Testes de segurança ofensivos com apoio de IA

Avaliação Final de Tecnologias Hackers (Insper, 2026.2).

Construímos um agente supervisionado que integra um LLM local (`qwen3:4b` via Ollama) a um conjunto limitado de ferramentas do Kali para investigar uma instância local do OWASP Juice Shop. Toda ação proposta pelo modelo passa por uma decisão humana (autorizar, modificar, rejeitar ou finalizar) e fica registrada em log.

## Topologia

O laboratório roda inteiro no Ubuntu Server do kit, atrás do pfSense montado no Roteiro 1.

```
 Notebook do grupo (Wi-Fi WannaCry)
   │ OpenVPN do grupo (10.8.0.x, split tunnel)
   ▼
 pfSense  WAN 192.168.20.26 ── LAN 10.0.80.1
   │
   ▼
 Ubuntu Server 10.0.80.3
   ├─ Ollama (qwen3:4b) ........ 127.0.0.1:11434
   ├─ Agente (Python) ── docker exec ──┐
   │                                   ▼
   └─ rede Docker "labnet" (internal, 172.31.80.0/24)
         ├─ kali       172.31.80.20  nmap, curl, ffuf, dirb
         └─ juiceshop  172.31.80.10  :3000
```

O escopo é garantido em três camadas:

1. **Código do agente:** só aceita o alvo `juiceshop:3000` e opções de uma lista permitida.
2. **Rede Docker:** `labnet` é `internal`, então os containers não têm rota para a internet, para a LAN do kit nem para o pfSense. Uma regra do `ufw` impede que alcancem serviços do próprio servidor pelo gateway da bridge. Nenhuma porta é publicada no host.
3. **Perímetro:** o pfSense não encaminha nenhuma porta para o Juice Shop; o acesso do grupo ao servidor é só pela VPN.

## Versões fixadas

| Componente | Versão |
|---|---|
| Ubuntu Server | 24.04.5 LTS |
| Docker / Compose | 29.1.3 / 2.40.3 |
| OWASP Juice Shop | `bkimminich/juice-shop:v20.3.0@sha256:cea5a4af4aacee498c491491af0408934ec81d004035c0a02ef3e54395e3bf27` |
| Kali (base) | `kalilinux/kali-rolling@sha256:ea20024e16833dab1a5337f5998602f3b81f8a38f3b0995dda272c83a1b0c1b9` |
| Ollama | v0.40.13 (instalado no espaço do usuário, sem sudo) |
| Modelo | `qwen3:4b` (digest registrado por `lab/check_env.sh`) |

As versões das ferramentas dentro do Kali são registradas pelo `lab/check_env.sh` em `lab/evidencias/`.

## Como reproduzir

### 1. Acesso ao servidor

1. Conectar o notebook ao Wi-Fi WannaCry e subir a VPN do grupo no cliente OpenVPN.
2. `ssh lr@10.0.80.3`

### 2. Pré-requisitos no servidor

Ubuntu Server 24.04 com Docker, Compose, `curl`, `zstd` e Python 3, e o usuário no grupo `docker`:

```bash
sudo apt install -y docker.io docker-compose-v2 curl zstd python3-venv
sudo usermod -aG docker $USER   # sair e entrar de novo
```

### 3. Instalação

```bash
git clone https://github.com/lucaskmk/IA-Testes-de-seguranca-ofensivos.git ~/af && cd ~/af
bash lab/install.sh
```

O script instala o Ollama em `~/.local/ollama`, sobe o servidor do modelo em loopback, baixa o `qwen3:4b`, constrói a imagem do Kali e sobe os containers `juiceshop` e `kali` na rede `labnet`.

### 4. Bloqueio dos containers para o próprio servidor (uma vez, com sudo)

```bash
sudo ufw insert 1 deny from 172.31.80.0/24
```

### 5. Verificação

```bash
bash lab/check_env.sh lab/evidencias/check_env_$(date +%Y%m%d_%H%M).txt
```

Todas as linhas devem sair `PASS`. O script confere versões, se o Ollama e o Juice Shop respondem, e se o Kali **não** alcança internet, pfSense, LAN nem os serviços do servidor.

### 6. Restauração do Juice Shop

```bash
bash lab/restore.sh lab/evidencias/restore_$(date +%Y%m%d_%H%M).txt
```

Recria o container (o estado da aplicação vive dentro dele) e confirma o estado inicial: HTTP 200 e nenhum desafio resolvido no placar. Para provar a transição, antes de recriar o script grava um marcador no container atual e anota o id e os desafios resolvidos; depois confere que o id mudou e que o marcador sumiu (falha se não). Rodamos o restore antes de cada investigação.

Teste manual complementar: criar uma conta pelo navegador, rodar o restore e confirmar que o login com essa conta passa a falhar.

### 7. Depois de reiniciar o servidor

Os containers voltam sozinhos (`restart: unless-stopped`). O Ollama precisa ser iniciado:

```bash
bash lab/ollama.sh start
```

## Agente supervisionado

Python 3.12 só com a biblioteca padrão (nada a instalar). Rodar na raiz do repositório, dentro de um `tmux` no servidor, para que uma queda da VPN não interrompa a sessão:

```bash
tmux new -s agente
python3 agent/agent.py --id I1 --objetivo "<objetivo da investigação>" --restore
```

Ciclo de cada turno:

1. O modelo recebe o objetivo, a lista de fatos que ele mesmo anotou até agora (apresentada como não verificada) e um histórico curto, e responde em JSON (`interpretacao`, `fatos_observados`, `acao`, `ferramenta`, `parametros`, `justificativa`, `conclusao`). JSON inválido gera uma nova tentativa com a mensagem de erro; as duas chamadas ficam registradas.
2. A trava de escopo (`agent/scope.py`) valida a proposta e monta o comando. Host e porta vêm da configuração; o modelo escolhe só caminho, método, cabeçalhos, corpo e flags de uma lista permitida.
3. O grupo marca se a proposta é **igual**, **diferente** ou **nova** em relação ao plano 3.1 (ou não se aplica) e decide: **[a]utorizar**, **[m]odificar** (troca ferramenta ou parâmetros), **[r]ejeitar** ou **[f]inalizar**, sempre com justificativa. Proposta bloqueada pela trava não pode ser autorizada.
4. A ferramenta roda no container `kali` (`docker exec`, sem shell). A saída completa vai para `logs/raw/`; um resumo truncado volta ao modelo.
5. O modelo interpreta o resultado e propõe o próximo passo. O grupo vê a interpretação **e o que mudou na lista de fatos do modelo** (o que entrou e o que saiu), e registra a decisão após o resultado, uma nova hipótese (se houver) e tags.

Tags aceitas (lista fixa, para as contagens não se fragmentarem): `boa_sugestao`, `alucinacao`, `interpretacao_errada`, `sem_base_no_resultado`, `repeticao`, `acao_desnecessaria`, `fora_escopo`, `json_invalido`, `falha_ia`.
6. Rejeições e modificações voltam ao modelo com o motivo, no turno seguinte.

| Ferramenta | Por baixo | Limites |
|---|---|---|
| `http_request` | curl | Alvo fixo `http://juiceshop:3000`; sem seguir redirecionamentos; cabeçalho `Host` bloqueado; corpo pela entrada padrão |
| `nmap_scan` | nmap | Alvo e porta fixos; flags `-sT -sV -Pn -n -T2/3/4 --version-light/--version-all --reason -v` |
| `dir_enum` | ffuf | Wordlists `dirb_small` ou `dirb_common`; 50 req/s; resumo por status e tamanho |
| `decode_jwt` | Python | Local, sem rede, sem verificar assinatura |

Configuração em `agent/config.example.toml` (modelo, temperatura 0.2, seed 42, `num_ctx` 8192, thinking desligado, limite de 15 turnos).

### Registros

| Arquivo | Conteúdo |
|---|---|
| `logs/investigacao_<id>.jsonl` | Um registro por turno: proposta, justificativa do modelo, fatos do modelo (lista e mudanças), relação com o plano do grupo, bloqueio de escopo, decisão e motivo, parâmetros e comando executados, resumo e SHA-256 da saída, interpretação do modelo, decisão do grupo após o resultado, nova hipótese, tags. Também o restore e o encerramento. O registro de início traz a versão do código (commit, alterações não commitadas e SHA-256 de cada arquivo do agente) |
| `logs/modelo_<id>.jsonl` | Cada chamada ao modelo: mensagens enviadas, resposta bruta, validação, tempos |
| `logs/raw/` | Saída completa de cada ferramenta |
| `logs/teste_escopo.jsonl` | Teste negativo da trava de escopo |
| `logs/revisao_plano.jsonl` | Revisão do plano pelo modelo (Fase 3.2) |

### Outros comandos

```bash
python3 -m unittest discover -s agent/tests -v   # testes da trava de escopo e da validação
python3 agent/teste_escopo.py                    # teste negativo documentado
python3 agent/revisar_plano.py                   # Fase 3.2: exige o plano commitado, sem alterações e no remoto
python3 agent/summarize_logs.py I1 I2 I3         # métricas, transcrições e conferência dos SHA-256 das saídas
```

### Depois de cada investigação

Os logs só existem no servidor até serem commitados. Logo ao terminar, no servidor:

```bash
python3 agent/summarize_logs.py <id>    # deve terminar com "OK" na integridade
```

E commit + push de `logs/` (direto do servidor, ou trazendo os arquivos para o notebook sem alterá-los):

```bash
git add logs/ && git commit -m "Logs da investigação <id>" && git push
```

O horário do push no GitHub fica como âncora de que os logs não foram alterados depois.

## Acesso manual ao alvo

- **Navegador:** com a VPN conectada, no notebook:
  ```bash
  ssh -L 3000:172.31.80.10:3000 lr@10.0.80.3
  ```
  e abrir `http://localhost:3000`. O Juice Shop continua rodando só no kit; o túnel apenas exibe a página.
- **Ferramentas do Kali:** `docker exec -it kali bash` (alvo `juiceshop:3000`).

## Estrutura do repositório

```
lab/            laboratório: compose, Kali, instalação, restore, verificação e evidências
agent/          agente supervisionado, prompts, testes e scripts de métricas
planejamento/   observações, plano de testes do grupo e revisão pelo LLM
logs/           registros JSONL de cada investigação e saídas brutas
investigacoes/  os seis itens de cada investigação
relatorio/      relatório técnico
```
