# Comparação de modelos locais

Responde à pergunta "outro modelo local se sai melhor que o `qwen3:4b`?". A ferramenta `agent/comparar_modelos.py` reenvia uma **decisão já registrada** (de `logs/modelo_<id>.jsonl`) a vários modelos do Ollama, com os **mesmos parâmetros** (temperatura 0,2, seed 42, `num_ctx` 8192) e o mesmo schema. Nenhuma ferramenta é executada — isola só o passo de decisão do modelo. Resultado bruto em `logs/comparacao_modelos.jsonl`.

Comparamos `qwen3:4b` (2,5 GB) e `llama3.2:3b` (2,0 GB) em três situações da investigação I2 (autorização).

| Situação (chamada) | `qwen3:4b` propõe | `llama3.2:3b` propõe |
|---|---|---|
| Obter uma sessão, após rejeitarmos o nmap (`I2-m002`) | `GET /login` — alucina um caminho de login (31 s) | `dir_enum` com wordlist `dirb_small\|dirb_common` — valor malformado, seria bloqueado pela trava (27 s) |
| Logar no endpoint correto (`I2-m003`) | `POST /rest/user/login` — **correto** (28 s) | `POST` com `{email,password}` — **correto** (33 s) |
| Qual recurso ler, já com o token (`I2-m004`) | `GET /api/Users/25` (o próprio id) (115 s) | `POST /api/Users` — **re-registra** a conta, fora de rumo (31 s) |

## Leitura

- **Nos dois modelos, 0 JSON inválido** — ambos respeitaram o formato.
- **No passo sem ambiguidade (o login), os dois acertam.** A diferença aparece nos passos novos ou ambíguos: o `qwen3` **alucina caminhos** (`/login`, e na investigação real `/api/auth/login`); o `llama3.2` propõe **ações malformadas ou fora de rumo** (wordlist inválida, re-registrar a conta). Nenhum dos dois conduz a investigação de autorização sozinho.
- **Trocar o modelo não remove a necessidade de supervisão; muda os modos de falha.** É um reforço direto da nossa conclusão: o valor está no humano que filtra e corrige, não na autonomia do modelo.
- **Tempo varia bastante** (28 a 115 s). O `qwen3` demorou 115 s na situação com o JWT longo no contexto — efeito do tamanho do contexto, uma limitação de integração.

## Nota de reprodutibilidade

Mesmo com `seed` fixa, a saída **não é perfeitamente determinística** entre execuções: aqui o `qwen3` propôs `/login`, mas na investigação original (mesma situação) propôs `/api/auth/login`. O Ollama/llama.cpp não garante determinismo total entre execuções (estado do cache KV, versão). Registramos isso como limitação: a seed reduz, mas não elimina, a variação — por isso as conclusões se apoiam nas respostas HTTP das ferramentas, não na repetibilidade exata das propostas do modelo.

## Como testar um modelo novo

```bash
ssh kit '~/.local/ollama/bin/ollama pull <modelo>'          # ex.: gemma2:2b, phi3:mini
python3 agent/comparar_modelos.py --chamada I2-m002 --modelos "qwen3:4b,<modelo>"
```

O mesmo vale para rodar uma investigação inteira com outro modelo: basta trocar `nome` em `agent/config.toml` e rodar `agent/agent.py` normalmente — o modelo e o digest ficam gravados em cada turno do log.
