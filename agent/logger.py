"""Registro das investigações em JSONL, gravado e sincronizado a cada turno.

Três arquivos por investigação:
- logs/investigacao_<id>.jsonl  um registro por turno (proposta, decisão, execução, interpretação, decisão do grupo)
- logs/modelo_<id>.jsonl        cada chamada ao modelo: mensagens enviadas, resposta bruta, validação
- logs/raw/<id>_turno<N>.txt    saída completa de cada ferramenta (o log guarda o resumo e o SHA-256)
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")


def agora() -> str:
    return datetime.now(FUSO).isoformat(timespec="seconds")


def sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class Registro:
    def __init__(self, pasta_logs: Path, investigacao: str):
        self.investigacao = investigacao
        self.sessao = f"{investigacao}-{agora()}"
        self.pasta = Path(pasta_logs)
        (self.pasta / "raw").mkdir(parents=True, exist_ok=True)
        self.arq_turnos = self.pasta / f"investigacao_{investigacao}.jsonl"
        self.arq_modelo = self.pasta / f"modelo_{investigacao}.jsonl"
        self._chamadas = sum(1 for _ in open(self.arq_modelo, encoding="utf-8")) if self.arq_modelo.exists() else 0

    def _anexar(self, arquivo: Path, registro: dict) -> None:
        with open(arquivo, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def turno(self, registro: dict) -> None:
        self._anexar(self.arq_turnos, {"investigacao": self.investigacao, "sessao": self.sessao,
                                       "timestamp": agora(), **registro})

    def chamada_modelo(self, mensagens: list[dict], resultado: dict, tentativa: int) -> str:
        self._chamadas += 1
        id_chamada = f"{self.investigacao}-m{self._chamadas:03d}"
        self._anexar(self.arq_modelo, {
            "id": id_chamada, "sessao": self.sessao, "timestamp": agora(), "tentativa": tentativa,
            "mensagens": mensagens, "resposta_bruta": resultado["bruto"], "json_valido": not resultado["erros"],
            "erros": resultado["erros"], "duracao_ms": resultado["duracao_ms"], "metricas": resultado["metricas"],
        })
        return id_chamada

    def saida_bruta(self, turno: int, texto: str) -> tuple[str, str]:
        nome = f"{self.investigacao}_{self.sessao[-25:].replace(':', '')}_turno{turno}.txt"
        caminho = self.pasta / "raw" / nome
        caminho.write_text(texto, encoding="utf-8")
        return str(caminho.relative_to(self.pasta.parent)).replace("\\", "/"), sha256(texto)
