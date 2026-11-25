#!/usr/bin/env bash
# Verifica versões, serviços e isolamento do laboratório. Rodar antes de cada investigação.
# Uso: lab/check_env.sh [arquivo_de_saida]   (sugestão: lab/evidencias/check_env_<data>.txt)
set -uo pipefail
export TZ=America/Sao_Paulo

SAIDA="${1:-/dev/null}"
OLLAMA_BIN="$HOME/.local/ollama/bin/ollama"
ALVO="http://172.31.80.10:3000"
DIGEST_MODELO="359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7"
falhas=0

ok()    { echo "PASS  $*"; }
falha() { echo "FAIL  $*"; falhas=$((falhas + 1)); }

# Tenta abrir uma conexão TCP a partir do container kali; sucesso = porta alcançável.
alcanca_do_kali() {
  docker exec kali timeout 4 bash -c "</dev/tcp/$1/$2" >/dev/null 2>&1
}

exec > >(tee -a "$SAIDA") 2>&1

{
  echo "# check_env $(date -Iseconds) em $(hostname)"

  echo "## Versões"
  echo "docker: $(docker --version)"
  echo "compose: $(docker compose version --short)"
  echo "ollama: $("$OLLAMA_BIN" --version 2>/dev/null | tail -1)"
  echo "modelo: $(OLLAMA_HOST=127.0.0.1:11434 "$OLLAMA_BIN" list 2>/dev/null | awk '$1=="qwen3:4b"{print $1, "id="$2, $3$4}')"
  echo "juiceshop: $(docker inspect juiceshop --format '{{.Config.Image}}' 2>/dev/null)"
  echo "kali: $(docker inspect kali --format '{{.Config.Image}} {{.Image}}' 2>/dev/null)"
  echo "kali/nmap: $(docker exec kali nmap --version 2>/dev/null | head -1)"
  echo "kali/curl: $(docker exec kali curl --version 2>/dev/null | head -1)"
  echo "kali/ffuf: $(docker exec kali ffuf -V 2>/dev/null | head -1)"

  echo "## Serviços"
  # Digest fixado do qwen3:4b usado em todos os logs; outro digest = outro modelo.
  digest=$(curl -fs -m 5 http://127.0.0.1:11434/api/tags | python3 -c '
import json, sys
print(next((m["digest"] for m in json.load(sys.stdin)["models"] if m["name"] == "qwen3:4b"), ""))' 2>/dev/null)
  if [[ "$digest" == "$DIGEST_MODELO" ]]; then ok "digest do qwen3:4b confere (${digest:0:12})"; else falha "digest do qwen3:4b diferente do fixado: '${digest:0:12}'"; fi
  if curl -fs -m 5 http://127.0.0.1:11434/api/version >/dev/null; then ok "Ollama responde em 127.0.0.1:11434"; else falha "Ollama não responde"; fi
  if ss -tlnH | awk '{print $4}' | grep -q '^127.0.0.1:11434$'; then ok "Ollama escuta só em loopback"; else falha "Ollama não está só em loopback"; fi
  if [[ "$(curl -s -o /dev/null -w '%{http_code}' -m 5 "$ALVO/")" == "200" ]]; then ok "Juice Shop responde ao host em $ALVO"; else falha "Juice Shop não responde ao host"; fi
  if docker exec kali curl -s -o /dev/null -m 5 -w '%{http_code}' http://juiceshop:3000/ | grep -q 200; then ok "kali alcança juiceshop:3000"; else falha "kali não alcança juiceshop:3000"; fi

  echo "## Isolamento"
  if [[ "$(docker network inspect labnet --format '{{.Internal}}')" == "true" ]]; then ok "labnet é internal (sem rota para fora)"; else falha "labnet não é internal"; fi
  if ss -tlnH | awk '{print $4}' | grep -q ':3000$'; then falha "há algo escutando na porta 3000 do host"; else ok "nenhuma porta 3000 publicada no host"; fi
  for destino in "1.1.1.1 443 internet" "10.0.80.1 80 pfSense" "10.0.80.3 22 SSH do servidor (IP da LAN)" \
                 "172.31.80.1 22 SSH do servidor (gateway da labnet)" "172.31.80.1 80 Apache do servidor (gateway)" \
                 "172.31.80.1 11434 Ollama (gateway)"; do
    set -- $destino
    ip=$1; porta=$2; shift 2
    if alcanca_do_kali "$ip" "$porta"; then falha "kali alcança $* ($ip:$porta)"; else ok "kali NÃO alcança $* ($ip:$porta)"; fi
  done
  if docker exec kali curl -s -m 5 -o /dev/null https://example.com; then falha "kali resolve e acessa a internet"; else ok "kali não acessa https://example.com"; fi

  echo "## Resultado: $falhas falha(s)"
}

exit $(( falhas > 0 ))
