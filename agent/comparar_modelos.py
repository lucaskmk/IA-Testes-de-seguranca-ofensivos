#!/usr/bin/env python3
"""Compara modelos locais no MESMO prompt registrado.

Reenvia uma chamada já gravada em `logs/modelo_<id>.jsonl` a vários modelos do Ollama,
com os mesmos parâmetros (temperatura, seed, num_ctx, schema), e tabula a proposta de cada
um. Nenhuma ferramenta é executada — é só o passo de decisão do modelo, isolado, para ver
qual modelo propõe o quê diante da mesma situação.

Uso:
    python3 agent/comparar_modelos.py --chamada I2-m002 --modelos "qwen3:4b,llama3.2:3b"

Saídas: `logs/comparacao_modelos.jsonl` (bruto) e `relatorio/comparacao_modelos.md` (tabela).
"""

import argparse
import json
import sys
from pathlib import Path

import config as configuracao
import llm
from logger import agora


def carregar_chamada(pasta_logs: Path, id_chamada: str) -> dict:
    investigacao = id_chamada.rsplit("-m", 1)[0]
    arquivo = pasta_logs / f"modelo_{investigacao}.jsonl"
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        registro = json.loads(linha)
        if registro.get("id") == id_chamada:
            return registro
    raise SystemExit(f"chamada {id_chamada} não encontrada em {arquivo}")


def _resumo_proposta(dados: dict | None) -> dict:
    if not dados:
        return {}
    return {k: dados.get(k) for k in ("acao", "ferramenta", "parametros", "justificativa")}


def main() -> int:
    ap = argparse.ArgumentParser(description="Compara modelos locais no mesmo prompt registrado")
    ap.add_argument("--chamada", required=True, help="id da chamada, ex.: I2-m002")
    ap.add_argument("--modelos", required=True, help="lista separada por vírgula, ex.: qwen3:4b,llama3.2:3b")
    args = ap.parse_args()

    cfg = configuracao.carregar()
    pasta = cfg["caminhos"]["logs"]
    original = carregar_chamada(pasta, args.chamada)
    mensagens = original["mensagens"][:2]  # sistema + usuário, sem as retentativas
    modelos = [m.strip() for m in args.modelos.split(",") if m.strip()]

    # Contexto da chamada: mostra a situação que todos os modelos vão enfrentar.
    contexto = mensagens[1]["content"]
    objetivo = next((l for l in contexto.splitlines() if l.startswith("OBJETIVO")), "")

    linhas = ["# Comparação de modelos locais", "",
              f"- Chamada reproduzida: `{args.chamada}` · {agora()}",
              f"- {objetivo}",
              f"- Parâmetros iguais para todos: temperatura {cfg['modelo']['temperature']}, seed {cfg['modelo']['seed']}, num_ctx {cfg['modelo']['num_ctx']}",
              "", "| Modelo | JSON válido | Tempo (s) | Ação | Ferramenta | Parâmetros |",
              "|---|---|---|---|---|---|"]
    registros = []
    print(f"Chamada {args.chamada} — {objetivo[:70]}\n")
    for nome in modelos:
        cfg["modelo"]["nome"] = nome
        print(f"[{nome}] consultando...", flush=True)
        res = llm.chamar(cfg, mensagens)
        prop = _resumo_proposta(res["dados"])
        params = json.dumps(prop.get("parametros", {}), ensure_ascii=False)
        linhas.append(f"| `{nome}` | {'sim' if not res['erros'] else 'não'} | {res['duracao_ms'] / 1000:.1f} | "
                      f"{prop.get('acao', '—')} | {prop.get('ferramenta', '—')} | `{params[:70]}` |")
        registros.append({"timestamp": agora(), "chamada": args.chamada, "modelo": nome,
                          "json_valido": not res["erros"], "erros": res["erros"],
                          "duracao_ms": res["duracao_ms"], "resposta_bruta": res["bruto"], "proposta": prop})
        print(f"  -> {prop.get('ferramenta', '—')} {params[:70]}  ({res['duracao_ms'] / 1000:.1f}s, "
              f"json {'ok' if not res['erros'] else 'inválido'})")

    with open(pasta / "comparacao_modelos.jsonl", "a", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    destino = pasta.parent / "relatorio" / "comparacao_modelos.md"
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"\nTabela em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
