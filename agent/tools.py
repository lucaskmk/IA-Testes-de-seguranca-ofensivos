"""Execução das ferramentas e resumo das saídas que voltam ao modelo.

As ferramentas de rede rodam dentro do container do Kali com `docker exec`, sem shell:
o argv montado pela trava de escopo é passado direto ao subprocess.
"""

import base64
import json
import subprocess
import time
from collections import Counter

from scope import Comando


def executar(cmd: Comando, cfg: dict) -> tuple[str, int, int]:
    """Executa o comando e devolve (saída completa, código de saída, duração em ms)."""
    inicio = time.monotonic()
    if cmd.local:
        saida, codigo = _decode_jwt(cmd.parametros["token"]), 0
    else:
        argv = ["docker", "exec", "-i", cfg["alvo"]["container"], *cmd.argv]
        try:
            proc = subprocess.run(argv, input=cmd.stdin or b"", capture_output=True,
                                  timeout=int(cfg["limites"]["timeout_ferramenta_s"]))
            saida = proc.stdout.decode("utf-8", "replace")
            if proc.stderr:
                saida += "\n[stderr]\n" + proc.stderr.decode("utf-8", "replace")
            codigo = proc.returncode
        except subprocess.TimeoutExpired:
            saida, codigo = f"[timeout após {cfg['limites']['timeout_ferramenta_s']} s]", -1
    return saida, codigo, int((time.monotonic() - inicio) * 1000)


def _b64url(parte: str) -> bytes:
    return base64.urlsafe_b64decode(parte + "=" * (-len(parte) % 4))


def _decode_jwt(token: str) -> str:
    cabecalho, carga, assinatura = token.split(".")
    linhas = []
    for nome, parte in (("header", cabecalho), ("payload", carga)):
        try:
            linhas.append(f"{nome}: {json.dumps(json.loads(_b64url(parte)), ensure_ascii=False, indent=2)}")
        except (ValueError, UnicodeDecodeError) as erro:
            linhas.append(f"{nome}: não decodificável ({erro})")
    linhas.append(f"assinatura: {len(assinatura)} caracteres (não verificada)")
    return "\n".join(linhas)


def _truncar(texto: str, limite: int) -> str:
    if len(texto) <= limite:
        return texto
    cabeca, cauda = int(limite * 0.75), int(limite * 0.2)
    omitidos = len(texto) - cabeca - cauda
    return f"{texto[:cabeca]}\n[... {omitidos} caracteres omitidos ...]\n{texto[-cauda:]}"


def resumir(ferramenta: str, saida: str, codigo: int, limite: int) -> str:
    """Texto que volta ao modelo: truncado e, no dir_enum, agregado por status e tamanho."""
    prefixo = f"[código de saída {codigo}, {len(saida)} caracteres]\n"
    if ferramenta == "dir_enum":
        return prefixo + _resumir_ffuf(saida, limite)
    return prefixo + _truncar(saida, limite)


def _resumir_ffuf(saida: str, limite: int) -> str:
    resultados = []
    for linha in saida.splitlines():
        linha = linha.strip()
        if linha.startswith("{"):
            try:
                resultados.append(json.loads(linha))
            except json.JSONDecodeError:
                pass
    if not resultados:
        return _truncar(saida, limite)
    grupos = Counter((r.get("status"), r.get("length")) for r in resultados)
    linhas = [f"{len(resultados)} respostas. Distribuição por (status, tamanho em bytes):"]
    linhas += [f"  status {s}, tamanho {t}: {n} caminhos" for (s, t), n in grupos.most_common(10)]
    # Caminhos fora do grupo mais comum são os que mais interessam; mostra esses primeiro.
    comum = grupos.most_common(1)[0][0]
    raros = [r for r in resultados if (r.get("status"), r.get("length")) != comum]
    linhas.append(f"Caminhos fora do grupo mais comum ({len(raros)}):")
    for r in raros[:60]:
        palavra = r.get("input", {}).get("FUZZ", "?")
        linhas.append(f"  /{palavra}  status={r.get('status')} tamanho={r.get('length')} palavras={r.get('words')}")
    return _truncar("\n".join(linhas), limite)


def linha_curta(ferramenta: str, saida: str) -> str:
    """Uma linha para o histórico resumido do prompt."""
    if ferramenta == "http_request":
        primeira = next((l for l in saida.splitlines() if l.startswith("HTTP/")), saida[:80])
        return f"{primeira.strip()} ({len(saida)} caracteres)"
    if ferramenta == "nmap_scan":
        porta = next((l for l in saida.splitlines() if "/tcp" in l), "sem linha de porta")
        return porta.strip()
    if ferramenta == "dir_enum":
        return f"{sum(1 for l in saida.splitlines() if l.startswith('{'))} respostas do ffuf"
    return saida.splitlines()[0][:120] if saida else "(vazio)"
