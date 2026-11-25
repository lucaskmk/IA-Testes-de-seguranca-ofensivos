#!/usr/bin/env bash
# Sobe, para ou consulta o servidor Ollama instalado no espaço do usuário (sem sudo).
# Uso: lab/ollama.sh start|stop|status
set -euo pipefail

OLLAMA_DIR="${OLLAMA_DIR:-$HOME/.local/ollama}"
OLLAMA_BIN="$OLLAMA_DIR/bin/ollama"
PID_FILE="$HOME/.ollama/serve.pid"
LOG_FILE="$HOME/.ollama/serve.log"

# Só loopback: o Ollama não tem autenticação.
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_KEEP_ALIVE=30m

rodando() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

case "${1:-status}" in
  start)
    if rodando; then
      echo "Ollama já está rodando (pid $(cat "$PID_FILE"))."
      exit 0
    fi
    mkdir -p "$(dirname "$PID_FILE")"
    nohup "$OLLAMA_BIN" serve >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
    for _ in $(seq 1 30); do
      if curl -fs http://127.0.0.1:11434/api/version >/dev/null; then
        echo "Ollama no ar: $(curl -fs http://127.0.0.1:11434/api/version)"
        exit 0
      fi
      sleep 1
    done
    echo "Ollama não respondeu em 30 s; veja $LOG_FILE" >&2
    exit 1
    ;;
  stop)
    if rodando; then
      kill "$(cat "$PID_FILE")"
      rm -f "$PID_FILE"
      echo "Ollama parado."
    else
      echo "Ollama não estava rodando."
    fi
    ;;
  status)
    if rodando; then
      echo "rodando (pid $(cat "$PID_FILE")): $(curl -fs http://127.0.0.1:11434/api/version || echo 'sem resposta')"
    else
      echo "parado"
      exit 1
    fi
    ;;
  *)
    echo "Uso: $0 start|stop|status" >&2
    exit 2
    ;;
esac
