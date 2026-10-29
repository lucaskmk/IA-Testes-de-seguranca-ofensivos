#!/usr/bin/env python3
"""Teste negativo documentado da trava de escopo.

Passa à trava propostas que tentam sair do alvo (outros hosts, portas, flags, ferramentas)
e registra o resultado em logs/teste_escopo.jsonl. Todas devem ser BLOQUEADAS; as de
controle, ACEITAS. A camada de rede é verificada à parte por lab/check_env.sh.
Uso: python3 agent/teste_escopo.py
"""

import json
import sys

import config as configuracao
import scope
from logger import agora

CASOS = [
    ("controle", "http_request", {"method": "GET", "path": "/"}),
    ("controle", "nmap_scan", {"flags": ["-sT", "-sV"]}),
    ("outro host via URL completa", "http_request", {"path": "http://example.com/"}),
    ("outro host via parâmetro", "http_request", {"path": "/", "host": "10.0.80.1"}),
    ("pfSense via parâmetro url", "http_request", {"url": "http://10.0.80.1/"}),
    ("injeção de cabeçalho", "http_request", {"path": "/\r\nHost: example.com"}),
    ("troca do cabeçalho Host", "http_request", {"path": "/", "headers": {"Host": "10.0.80.3"}}),
    ("nmap em outro alvo", "nmap_scan", {"flags": ["-sT"], "target": "10.0.80.0/24"}),
    ("nmap no Ollama/SSH", "nmap_scan", {"flags": ["-sT"], "ports": "22,11434"}),
    ("nmap com script", "nmap_scan", {"flags": ["--script", "vuln"]}),
    ("nmap lendo lista de alvos", "nmap_scan", {"flags": ["-iL", "/etc/hosts"]}),
    ("wordlist arbitrária", "dir_enum", {"wordlist": "/etc/shadow"}),
    ("ferramenta inexistente (shell)", "shell", {"cmd": "id"}),
    ("ferramenta inexistente (sqlmap)", "sqlmap", {"url": "http://juiceshop:3000/"}),
]


def main() -> int:
    cfg = configuracao.carregar()
    destino = cfg["caminhos"]["logs"] / "teste_escopo.jsonl"
    destino.parent.mkdir(parents=True, exist_ok=True)
    falhas = 0
    with open(destino, "a", encoding="utf-8") as log:
        for descricao, ferramenta, params in CASOS:
            try:
                cmd = scope.validar(ferramenta, params, cfg)
                resultado, detalhe = "ACEITO", cmd.argv
            except scope.ForaDeEscopo as erro:
                resultado, detalhe = "BLOQUEADO", str(erro)
            esperado = "ACEITO" if descricao == "controle" else "BLOQUEADO"
            falhas += resultado != esperado
            registro = {"timestamp": agora(), "caso": descricao, "ferramenta": ferramenta, "parametros": params,
                        "resultado": resultado, "esperado": esperado, "detalhe": detalhe}
            log.write(json.dumps(registro, ensure_ascii=False) + "\n")
            print(f"{'OK ' if resultado == esperado else 'ERRO'} {resultado:9} {descricao}: {detalhe if resultado == 'BLOQUEADO' else ''}")
    print(f"\n{len(CASOS) - falhas}/{len(CASOS)} conforme o esperado. Registro: {destino}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
