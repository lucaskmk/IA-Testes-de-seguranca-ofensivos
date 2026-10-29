#!/usr/bin/env bash
# Recria o container do Juice Shop e verifica que ele voltou ao estado inicial.
# O estado da aplicação (SQLite e arquivos) vive dentro do container, então recriá-lo
# zera tudo. Quem executa é o grupo; o restore não é ferramenta do agente.
# Uso: lab/restore.sh [arquivo_de_saida]
set -euo pipefail
export TZ=America/Sao_Paulo

LAB_DIR="$(cd "$(dirname "$0")" && pwd)"
ALVO="http://172.31.80.10:3000"
SAIDA="${1:-/dev/null}"

exec > >(tee -a "$SAIDA") 2>&1

{
  echo "restore_inicio=$(date -Iseconds)"
  docker compose -f "$LAB_DIR/docker-compose.yml" up -d --force-recreate juiceshop

  for i in $(seq 1 120); do
    if [[ "$(curl -s -o /dev/null -w '%{http_code}' -m 3 "$ALVO/")" == "200" ]]; then
      echo "http_200_apos_s=$i"
      break
    fi
    sleep 1
    if [[ $i -eq 120 ]]; then
      echo "ERRO: Juice Shop não respondeu em 120 s" >&2
      exit 1
    fi
  done

  echo "container_criado=$(docker inspect juiceshop --format '{{.Created}}')"
  echo "imagem=$(docker inspect juiceshop --format '{{.Image}}')"

  # Estado inicial: nenhum desafio resolvido no placar da aplicação.
  resolvidos=$(curl -fs -m 10 "$ALVO/api/Challenges" | python3 -c '
import json, sys
dados = json.load(sys.stdin)["data"]
print(sum(1 for d in dados if d.get("solved")))
')
  echo "desafios_resolvidos=$resolvidos"
  if [[ "$resolvidos" != "0" ]]; then
    echo "ERRO: estado inicial não confirmado" >&2
    exit 1
  fi
  echo "restore_fim=$(date -Iseconds) status=OK"
}
