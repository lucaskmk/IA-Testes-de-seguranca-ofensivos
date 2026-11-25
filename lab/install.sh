#!/usr/bin/env bash
# Prepara o laboratório no Ubuntu Server do kit. Roda como usuário comum que esteja no
# grupo "docker"; nada aqui usa sudo. O único passo com sudo (regra do ufw) é impresso
# no final para o grupo executar.
set -euo pipefail

OLLAMA_VERSION="v0.40.13"
MODELO="qwen3:4b"
OLLAMA_DIR="$HOME/.local/ollama"
LAB_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "== 1. Pré-requisitos"
id -nG | grep -qw docker || { echo "Usuário não está no grupo docker." >&2; exit 1; }
for cmd in docker curl zstd tar python3; do
  command -v "$cmd" >/dev/null || { echo "Falta o comando: $cmd" >&2; exit 1; }
done
docker compose version

echo "== 2. Ollama $OLLAMA_VERSION em $OLLAMA_DIR"
if [[ -x "$OLLAMA_DIR/bin/ollama" ]] && "$OLLAMA_DIR/bin/ollama" --version 2>/dev/null | grep -q "${OLLAMA_VERSION#v}"; then
  echo "já instalado"
else
  mkdir -p "$OLLAMA_DIR"
  curl -fL "https://github.com/ollama/ollama/releases/download/$OLLAMA_VERSION/ollama-linux-amd64.tar.zst" -o /tmp/ollama.tar.zst
  zstd -dc /tmp/ollama.tar.zst | tar -xf - -C "$OLLAMA_DIR"
  rm -f /tmp/ollama.tar.zst
fi
"$LAB_DIR/ollama.sh" start

echo "== 3. Modelo $MODELO"
OLLAMA_HOST=127.0.0.1:11434 "$OLLAMA_DIR/bin/ollama" pull "$MODELO"
OLLAMA_HOST=127.0.0.1:11434 "$OLLAMA_DIR/bin/ollama" list

echo "== 4. Containers (juiceshop + kali na rede interna labnet)"
docker compose -f "$LAB_DIR/docker-compose.yml" build
docker compose -f "$LAB_DIR/docker-compose.yml" up -d
docker compose -f "$LAB_DIR/docker-compose.yml" ps

cat <<'EOF'

== 5. Passo com sudo (uma vez, feito pelo grupo)
A rede labnet não tem saída, mas os containers ainda alcançam serviços do próprio
servidor pelo gateway 172.31.80.1 (SSH, Apache). Para bloquear:

    sudo ufw insert 1 deny from 172.31.80.0/24

Depois rode lab/check_env.sh para registrar os testes de isolamento.
EOF
