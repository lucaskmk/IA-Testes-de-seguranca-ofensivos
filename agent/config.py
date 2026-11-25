"""Carrega a configuração do agente (TOML) e resolve os caminhos a partir da raiz do repositório."""

import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_AGENTE = RAIZ / "agent"


def carregar(caminho: str | None = None) -> dict:
    if caminho:
        arquivo = Path(caminho)
    elif (PASTA_AGENTE / "config.toml").exists():
        arquivo = PASTA_AGENTE / "config.toml"
    else:
        arquivo = PASTA_AGENTE / "config.example.toml"
    with open(arquivo, "rb") as f:
        cfg = tomllib.load(f)
    cfg["_caminho"] = arquivo.resolve()
    cfg["_arquivo"] = str(arquivo.relative_to(RAIZ)) if arquivo.is_relative_to(RAIZ) else str(arquivo)
    for chave, valor in cfg["caminhos"].items():
        cfg["caminhos"][chave] = RAIZ / valor
    return cfg
