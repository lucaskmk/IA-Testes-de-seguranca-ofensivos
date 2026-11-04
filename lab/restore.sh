#!/usr/bin/env bash
# Recria o container do Juice Shop e verifica que ele voltou ao estado inicial.
# O estado da aplicação (SQLite e arquivos) vive dentro do container, então recriá-lo
# zera tudo. Para provar a transição, antes de recriar o script grava um marcador no
# container atual e anota o id e os desafios resolvidos; depois confere que o id mudou
# e o marcador sumiu. Quem executa é o grupo; o restore não é ferramenta do agente.
# Uso: lab/restore.sh [arquivo_de_saida]
set -euo pipefail
export TZ=America/Sao_Paulo

LAB_DIR="$(cd "$(dirname "$0")" && pwd)"
ALVO="http://172.31.80.10:3000"
SAIDA="${1:-/dev/null}"
MARCADOR=/tmp/marcador_restore

exec > >(tee -a "$SAIDA") 2>&1

desafios_resolvidos() {
  curl -fs -m 10 "$ALVO/api/Challenges" | python3 -c '
import json, sys
print(sum(1 for d in json.load(sys.stdin)["data"] if d.get("solved")))
'
}

{
  echo "restore_inicio=$(date -Iseconds)"

  id_antes=$(docker inspect juiceshop --format '{{.Id}}' 2>/dev/null || true)
  marcador_gravado=nao
  if [[ -n "$id_antes" ]]; then
    echo "container_antes=${id_antes:0:12}"
    echo "desafios_resolvidos_antes=$(desafios_resolvidos || echo '?')"
    tmp=$(mktemp)
    echo "gravado antes do restore em $(date -Iseconds)" >"$tmp"
    if docker cp "$tmp" "juiceshop:$MARCADOR"; then marcador_gravado=sim; fi
    rm -f "$tmp"
    echo "marcador_gravado=$marcador_gravado"
  else
    echo "container_antes=inexistente (primeira subida)"
  fi

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

  id_depois=$(docker inspect juiceshop --format '{{.Id}}')
  echo "container_depois=${id_depois:0:12}"
  echo "container_criado=$(docker inspect juiceshop --format '{{.Created}}')"
  echo "imagem=$(docker inspect juiceshop --format '{{.Image}}')"
  if [[ "$id_depois" == "$id_antes" ]]; then
    echo "ERRO: o container não foi recriado" >&2
    exit 1
  fi
  if [[ "$marcador_gravado" == sim ]]; then
    if docker cp "juiceshop:$MARCADOR" - >/dev/null 2>&1; then
      echo "ERRO: o marcador gravado antes do restore continua no container" >&2
      exit 1
    fi
    echo "marcador_apos_restore=ausente"
  fi

  # Estado inicial: nenhum desafio resolvido no placar da aplicação.
  resolvidos=$(desafios_resolvidos)
  echo "desafios_resolvidos=$resolvidos"
  if [[ "$resolvidos" != "0" ]]; then
    echo "ERRO: estado inicial não confirmado" >&2
    exit 1
  fi
  echo "restore_fim=$(date -Iseconds) status=OK"
}
