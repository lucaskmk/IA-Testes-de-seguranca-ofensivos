# Comparação de modelos locais

Responde à pergunta "outro modelo local se sai melhor que o `qwen3:4b`?". A ferramenta `agent/comparar_modelos.py` reenvia uma **decisão já registrada** (de `logs/modelo_<id>.jsonl`) a vários modelos do Ollama, com os **mesmos parâmetros** (temperatura 0,2, seed 42, `num_ctx` 8192) e o mesmo schema. Nenhuma ferramenta é executada — isola só o passo de decisão do modelo. Resultado bruto em `logs/comparacao_modelos.jsonl`.

Comparamos três modelos em três situações da investigação I2 (autorização): `qwen3:4b` (2,5 GB), `llama3.2:3b` (2,0 GB) e `gemma2:2b` (1,6 GB).

| Situação (chamada) | `qwen3:4b` | `llama3.2:3b` | `gemma2:2b` |
|---|---|---|---|
| Obter uma sessão, após rejeitar o nmap (`I2-m002`) | alucina `GET /login` | `dir_enum` com wordlist malformada | **copia o exemplo do prompt** (`GET /caminho?query`) |
| Logar no endpoint correto (`I2-m003`) | **acerta** `POST /rest/user/login` | **acerta** `POST` com `{email,password}` | **erra** — `POST /api/Users` (re-registra) |
| Qual recurso ler, já com o token (`I2-m004`) | `GET /api/Users/25` (próprio id) | `POST /api/Users` (re-registra) | `GET /api/Users` (a coleção) |
| Tempo típico | 28–115 s | 27–33 s | 17–30 s |

## Leitura

- **Os três respeitaram o formato** — 0 JSON inválido em todas as chamadas. Isso é o que o 4B fazia bem, e os outros também fazem.
- **No passo sem ambiguidade (o login), só o `qwen3` e o `llama3.2` acertam.** O `gemma2:2b` falha até aí — e, na primeira situação, ele **ecoou o exemplo do próprio prompt de sistema** (`/caminho?query`, header `Nome: valor`), um sintoma claro de um modelo pequeno demais para a tarefa.
- **Ranking qualitativo:** `qwen3:4b` ≳ `llama3.2:3b` > `gemma2:2b`. Mas **nenhum conduz a investigação sozinho** — todos falham nos passos novos ou ambíguos, cada um de um jeito (o `qwen3` alucina caminhos; o `llama3.2` propõe ações malformadas ou re-registra; o `gemma2` copia exemplos e erra o login).
- **Conclusão:** trocar o modelo **muda os modos de falha, não a necessidade de supervisão**. Modelos maiores (ou mais bem ajustados a seguir instruções) erram menos no óbvio, mas a decisão técnica continua dependendo do humano. É um reforço direto da tese do trabalho.
- **Tempo** varia com o modelo e com o tamanho do contexto: o `gemma2` foi o mais rápido (17–30 s); o `qwen3` chegou a 115 s na situação com o JWT longo no contexto.

## Nota de reprodutibilidade

Mesmo com `seed` fixa, a saída **não é perfeitamente determinística** entre execuções: o `qwen3` propôs `/login` aqui, mas `/api/auth/login` na investigação original (mesma situação). O Ollama/llama.cpp não garante determinismo total entre execuções (estado do cache KV, versão). Por isso as conclusões se apoiam nas respostas HTTP das ferramentas, não na repetição exata das propostas do modelo.

## Como testar um modelo novo

```bash
ssh kit '~/.local/ollama/bin/ollama pull <modelo>'          # ex.: phi3:mini, mistral:7b
python3 agent/comparar_modelos.py --chamada I2-m002 --modelos "qwen3:4b,<modelo>"
```

Para rodar uma investigação inteira com outro modelo, troque `nome` em `agent/config.toml` e rode `agent/agent.py` normalmente — o modelo e o digest ficam gravados em cada turno do log.
