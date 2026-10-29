#!/usr/bin/env python3
"""Gera métricas e transcrições legíveis a partir dos logs JSONL (os logs não são alterados).

Saídas:
- relatorio/metricas.md                 tabela por investigação (decisões, falhas de JSON, repetições, tags, tempos)
- logs/investigacao_<id>.md             transcrição turno a turno, para leitura e citação
Uso: python3 agent/summarize_logs.py [IDs...]   (sem IDs: todas as investigações em logs/)
"""

import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LOGS = RAIZ / "logs"


def ler_jsonl(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]


def metricas(inv: str) -> dict:
    registros = ler_jsonl(LOGS / f"investigacao_{inv}.jsonl")
    chamadas = ler_jsonl(LOGS / f"modelo_{inv}.jsonl")
    turnos = [r for r in registros if r.get("tipo") == "turno"]
    decisoes = Counter(r.get("decisao_humana") for r in turnos)
    tags = Counter(t for r in turnos for t in r.get("tags") or [])
    tempos = [c["duracao_ms"] for c in chamadas if c.get("duracao_ms")]
    encerr = [r for r in registros if r.get("tipo") == "encerramento"]
    return {
        "id": inv,
        "sessoes": len({r["sessao"] for r in registros}),
        "turnos": len(turnos),
        "decisoes": decisoes,
        "chamadas_modelo": len(chamadas),
        "json_invalido": sum(1 for c in chamadas if not c.get("json_valido")),
        "turnos_com_retentativa": sum(1 for r in turnos if r.get("tentativas", 1) > 1),
        "repeticoes": sum(1 for r in turnos if r.get("repete_turno")),
        "bloqueios_escopo": sum(1 for r in turnos if r.get("bloqueio_escopo")),
        "novas_hipoteses": sum(1 for r in turnos if r.get("nova_hipotese")),
        "tags": tags,
        "tempo_medio_modelo_s": round(sum(tempos) / len(tempos) / 1000, 1) if tempos else None,
        "conclusao": encerr[-1].get("classificacao") if encerr else None,
    }


def pct(n: int, total: int) -> str:
    return f"{n} ({100 * n / total:.0f}%)" if total else "0"


def tabela(lista: list[dict]) -> str:
    linhas = ["| Investigação | Turnos | Autorizado | Modificado | Rejeitado | Finalizado | Chamadas ao modelo | JSON inválido | Repetições | Bloqueios de escopo | Novas hipóteses | Tempo médio do modelo (s) | Conclusão |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in lista:
        d, t = m["decisoes"], m["turnos"]
        linhas.append(f"| {m['id']} | {t} | {pct(d['AUTORIZADO'], t)} | {pct(d['MODIFICADO'], t)} | {pct(d['REJEITADO'], t)} | "
                      f"{pct(d['FINALIZADO'], t)} | {m['chamadas_modelo']} | {m['json_invalido']} | {m['repeticoes']} | "
                      f"{m['bloqueios_escopo']} | {m['novas_hipoteses']} | {m['tempo_medio_modelo_s']} | {m['conclusao'] or '—'} |")
    linhas += ["", "Tags marcadas pelo grupo durante as investigações:", ""]
    for m in lista:
        linhas.append(f"- {m['id']}: " + (", ".join(f"{k} ×{v}" for k, v in m["tags"].most_common()) or "nenhuma"))
    return "\n".join(linhas)


def transcricao(inv: str) -> str:
    saida = [f"# Transcrição da investigação {inv}", "",
             f"Gerada a partir de `logs/investigacao_{inv}.jsonl` (fonte de verdade). Citação: `investigacao_{inv}.jsonl, turno N`.", ""]
    for r in ler_jsonl(LOGS / f"investigacao_{inv}.jsonl"):
        tipo = r.get("tipo")
        if tipo == "inicio":
            cfg = r.get("config", {})
            saida += [f"## Sessão {r['sessao']}", "", f"- Objetivo entregue ao modelo: {r['objetivo']}",
                      f"- Modelo: {cfg.get('modelo', {}).get('nome')} (digest {cfg.get('modelo', {}).get('digest')}), "
                      f"temperature {cfg.get('temperature')}, seed {cfg.get('seed')}",
                      f"- Restore nesta sessão: {r.get('restore_nesta_sessao')}", ""]
        elif tipo == "restore":
            saida += [f"**Restore** ({r['timestamp']}): {r['status']}", ""]
        elif tipo == "turno":
            saida += [f"### Turno {r['turno']} — {r.get('decisao_humana')}", "",
                      f"- Proposta: `{r.get('ferramenta_proposta')}` `{json.dumps(r.get('parametros_propostos'), ensure_ascii=False)}`",
                      f"- Justificativa do modelo: {r.get('justificativa_modelo')}"]
            if r.get("bloqueio_escopo"):
                saida.append(f"- Bloqueio da trava de escopo: {r['bloqueio_escopo']}")
            if r.get("repete_turno"):
                saida.append(f"- Repete a proposta do turno {r['repete_turno']}")
            saida.append(f"- Decisão do grupo: **{r.get('decisao_humana')}** — {r.get('motivo_decisao') or '(sem justificativa)'}")
            if r.get("parametros_executados") is not None:
                saida += [f"- Executado: `{json.dumps(r['parametros_executados'], ensure_ascii=False)}` (saída completa: `{r.get('saida_arquivo')}`)",
                          "", "```", (r.get("saida_resumo") or "")[:1500], "```", "",
                          f"- Interpretação do modelo: {r.get('interpretacao_modelo')}",
                          f"- Decisão do grupo após o resultado: {r.get('decisao_grupo_pos_resultado')}"]
            if r.get("nova_hipotese"):
                saida.append(f"- Nova hipótese: {r['nova_hipotese']}")
            if r.get("tags"):
                saida.append(f"- Tags: {', '.join(r['tags'])}")
            saida.append("")
        elif tipo == "encerramento":
            saida += ["## Encerramento", "", f"- Conclusão do grupo: **{r.get('classificacao')}** — {r.get('conclusao_grupo')}",
                      f"- Limitações: {r.get('limitacoes')}", f"- Conclusão proposta pelo modelo: {r.get('conclusao_modelo')}", ""]
        elif tipo == "interrompido":
            saida += [f"**Sessão interrompida** após {r.get('turnos')} turnos.", ""]
    return "\n".join(saida)


def main() -> None:
    ids = sys.argv[1:] or sorted(p.stem.removeprefix("investigacao_") for p in LOGS.glob("investigacao_*.jsonl"))
    lista = [metricas(i) for i in ids]
    (RAIZ / "relatorio").mkdir(exist_ok=True)
    (RAIZ / "relatorio" / "metricas.md").write_text("# Métricas das investigações\n\n" + tabela(lista) + "\n", encoding="utf-8")
    for i in ids:
        (LOGS / f"investigacao_{i}.md").write_text(transcricao(i), encoding="utf-8")
    print(tabela(lista))


if __name__ == "__main__":
    main()
