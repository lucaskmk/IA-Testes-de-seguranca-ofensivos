#!/usr/bin/env python3
"""Replay de uma chamada registrada ao modelo, para medir o efeito do resultado na decisão.

Pega uma chamada de logs/modelo_<id>.jsonl e a reenvia ao modelo com os mesmos parâmetros:
- --repetir: sem nenhuma mudança (linha de base: o quanto a resposta varia sozinha);
- --evento-arquivo: trocando só o bloco "ÚLTIMO EVENTO" (o resultado da ferramenta) pelo texto
  do arquivo. Tudo o mais (objetivo, fatos, histórico, prompt de sistema) fica idêntico.
Nenhuma ferramenta é executada. Cada replay vai para logs/replay_<id>.jsonl.

Uso:
    python3 agent/replay.py --chamada I2-m007 --repetir
    python3 agent/replay.py --chamada I2-m007 --evento-arquivo alt.txt --rotulo "200 trocado por 401"
"""

import argparse
import json
import sys
from pathlib import Path

import config as configuracao
import llm
from logger import agora, sha256

INICIO_EVENTO = "ÚLTIMO EVENTO:\n"
FIM_EVENTO = "\n\nResponda com o objeto JSON pedido."


def trocar_evento(mensagem: str, novo_evento: str) -> tuple[str, str]:
    """Devolve (mensagem com o evento trocado, evento original)."""
    i = mensagem.index(INICIO_EVENTO) + len(INICIO_EVENTO)
    j = mensagem.index(FIM_EVENTO, i)
    return mensagem[:i] + novo_evento + mensagem[j:], mensagem[i:j]


def _proposta(dados: dict | None) -> dict | None:
    if not dados:
        return None
    return {k: dados.get(k) for k in ("acao", "ferramenta", "parametros", "justificativa", "conclusao")}


def carregar_chamada(pasta_logs: Path, id_chamada: str) -> dict:
    investigacao = id_chamada.rsplit("-m", 1)[0]
    arquivo = pasta_logs / f"modelo_{investigacao}.jsonl"
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        registro = json.loads(linha)
        if registro.get("id") == id_chamada:
            return registro
    raise SystemExit(f"chamada {id_chamada} não encontrada em {arquivo}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay contrafactual de uma chamada ao modelo")
    ap.add_argument("--chamada", required=True, help="id da chamada, ex.: I2-m007")
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--repetir", action="store_true", help="reenvia sem mudanças (linha de base)")
    modo.add_argument("--evento-arquivo", help="arquivo com o texto que substitui o bloco ÚLTIMO EVENTO")
    ap.add_argument("--rotulo", default="", help="descrição curta da troca, para o relatório")
    args = ap.parse_args()

    cfg = configuracao.carregar()
    pasta_logs = cfg["caminhos"]["logs"]
    original = carregar_chamada(pasta_logs, args.chamada)
    mensagens = [dict(m) for m in original["mensagens"][:2]]  # sistema + usuário, sem as retentativas
    evento_original = None
    if args.evento_arquivo:
        novo = Path(args.evento_arquivo).read_text(encoding="utf-8").strip()
        mensagens[1]["content"], evento_original = trocar_evento(mensagens[1]["content"], novo)

    try:
        dados_originais = json.loads(original["resposta_bruta"])
    except (json.JSONDecodeError, TypeError):
        dados_originais = None
    resultado = llm.chamar(cfg, mensagens)
    antes, depois = _proposta(dados_originais), _proposta(resultado["dados"])
    mesma_acao = bool(antes and depois and all(antes[k] == depois[k] for k in ("acao", "ferramenta", "parametros")))

    registro = {
        "timestamp": agora(), "chamada_original": args.chamada,
        "modo": "repetir" if args.repetir else "contrafactual", "rotulo": args.rotulo,
        "modelo": cfg["modelo"]["nome"], "temperature": cfg["modelo"]["temperature"], "seed": cfg["modelo"]["seed"],
        "evento_original_sha256": sha256(evento_original) if evento_original is not None else None,
        "evento_novo": mensagens[1]["content"].split(INICIO_EVENTO, 1)[1].split(FIM_EVENTO, 1)[0] if args.evento_arquivo else None,
        "mensagens": mensagens, "resposta_bruta": resultado["bruto"], "erros": resultado["erros"],
        "duracao_ms": resultado["duracao_ms"], "proposta_original": antes, "proposta_nova": depois,
        "mesma_acao_ferramenta_parametros": mesma_acao,
    }
    investigacao = args.chamada.rsplit("-m", 1)[0]
    destino = pasta_logs / f"replay_{investigacao}.jsonl"
    with open(destino, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    print(f"Original : {json.dumps(antes, ensure_ascii=False)}")
    print(f"Replay   : {json.dumps(depois, ensure_ascii=False)}")
    print(f"Mesma ação/ferramenta/parâmetros: {mesma_acao} · registro em {destino}")
    return 0 if not resultado["erros"] else 2


if __name__ == "__main__":
    sys.exit(main())
