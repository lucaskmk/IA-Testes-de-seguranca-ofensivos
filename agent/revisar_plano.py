#!/usr/bin/env python3
"""Fase 3.2: envia o plano do grupo ao modelo local e prepara a tabela de decisões.

Só deve rodar depois que planejamento/plano_testes_grupo.md estiver commitado e enviado ao
remoto. Grava a chamada em logs/revisao_plano.jsonl e cria planejamento/revisao_llm.md com
a resposta bruta e a tabela; as colunas de decisão e justificativa são preenchidas pelo grupo.
Uso: python3 agent/revisar_plano.py
"""

import json
import subprocess
import sys
import time
import urllib.request

import config as configuracao
from logger import agora, sha256

SCHEMA = {
    "type": "object",
    "properties": {"sugestoes": {"type": "array", "items": {"type": "object", "properties": {
        "parte_do_plano": {"type": "string"}, "tipo": {"type": "string"},
        "sugestao": {"type": "string"}, "motivo": {"type": "string"}},
        "required": ["parte_do_plano", "tipo", "sugestao", "motivo"]}}},
    "required": ["sugestoes"],
}


def commit_do_plano(caminho) -> str:
    proc = subprocess.run(["git", "log", "-1", "--format=%H %cI", "--", str(caminho)],
                          capture_output=True, text=True, cwd=caminho.parent.parent)
    return proc.stdout.strip() or "plano não commitado"


def main() -> int:
    cfg = configuracao.carregar()
    raiz = cfg["caminhos"]["logs"].parent
    plano = raiz / "planejamento" / "plano_testes_grupo.md"
    if not plano.exists():
        print(f"Plano não encontrado: {plano}", file=sys.stderr)
        return 1
    commit = commit_do_plano(plano)
    if commit == "plano não commitado":
        print("O plano precisa estar commitado (e enviado ao remoto) antes da revisão.", file=sys.stderr)
        return 1

    instrucao = cfg["caminhos"]["prompt_revisao"].read_text(encoding="utf-8")
    texto_plano = plano.read_text(encoding="utf-8")
    m = cfg["modelo"]
    mensagens = [{"role": "system", "content": instrucao}, {"role": "user", "content": "PLANO DO GRUPO:\n\n" + texto_plano}]
    corpo = {"model": m["nome"], "messages": mensagens, "stream": False, "think": bool(m["think"]), "format": SCHEMA,
             "options": {"temperature": m["temperature"], "seed": m["seed"], "num_ctx": max(int(m["num_ctx"]), 16384)}}
    print("[consultando o modelo...]", flush=True)
    inicio = time.monotonic()
    req = urllib.request.Request(m["url"].rstrip("/") + "/api/chat", data=json.dumps(corpo).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=int(m["timeout_s"])) as resp:
        resposta = json.loads(resp.read())
    duracao = int((time.monotonic() - inicio) * 1000)
    bruto = resposta.get("message", {}).get("content", "")
    try:
        sugestoes = json.loads(bruto)["sugestoes"]
        valido = True
    except (json.JSONDecodeError, KeyError, TypeError):
        sugestoes, valido = [], False

    registro = {"timestamp": agora(), "plano_commit": commit, "plano_sha256": sha256(texto_plano),
                "prompt_sha256": sha256(instrucao), "modelo": m["nome"], "temperature": m["temperature"],
                "seed": m["seed"], "mensagens": mensagens, "resposta_bruta": bruto, "json_valido": valido,
                "duracao_ms": duracao}
    with open(raiz / "logs" / "revisao_plano.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    linhas = ["# Revisão do plano pelo LLM (Fase 3.2)", "",
              f"- Plano revisado: `planejamento/plano_testes_grupo.md`, commit `{commit}`",
              f"- Chamada registrada em `logs/revisao_plano.jsonl` ({registro['timestamp']}, {duracao / 1000:.0f} s, modelo {m['nome']}, seed {m['seed']})",
              "", "## Decisões do grupo", "",
              "| # | Parte do plano | Tipo | Sugestão do modelo | Decisão (aceita/modificada/rejeitada) | Justificativa técnica |",
              "|---|---|---|---|---|---|"]
    for i, s in enumerate(sugestoes, 1):
        celula = lambda v: str(v).replace("|", "\\|").replace("\n", " ")  # noqa: E731
        linhas.append(f"| {i} | {celula(s.get('parte_do_plano'))} | {celula(s.get('tipo'))} | "
                      f"{celula(s.get('sugestao'))} (motivo do modelo: {celula(s.get('motivo'))}) |  |  |")
    linhas += ["", "## Resposta bruta do modelo", "", "```json", bruto, "```", ""]
    destino = raiz / "planejamento" / "revisao_llm.md"
    destino.write_text("\n".join(linhas), encoding="utf-8")
    print(f"{len(sugestoes)} sugestões. Tabela em {destino}; preencha decisão e justificativa de cada linha.")
    return 0 if valido else 2


if __name__ == "__main__":
    sys.exit(main())
