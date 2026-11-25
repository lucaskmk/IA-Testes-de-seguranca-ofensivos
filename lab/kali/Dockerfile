# Estação de ataque usada pelo agente e pelo grupo.
# Base fixada por digest; as versões das ferramentas instaladas ficam registradas pelo check_env.sh.
FROM kalilinux/kali-rolling@sha256:ea20024e16833dab1a5337f5998602f3b81f8a38f3b0995dda272c83a1b0c1b9

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      nmap curl ffuf dirb ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /root
