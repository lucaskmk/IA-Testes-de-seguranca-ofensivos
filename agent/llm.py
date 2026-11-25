"""Cliente do Ollama (/api/chat) com saída estruturada e validação da resposta."""

import json
import time
import urllib.error
import urllib.request

from scope import FERRAMENTAS

# Formato exigido do modelo em todo turno. Vai como "format" para o Ollama e também é
# conferido aqui, porque um modelo pequeno pode devolver JSON incompleto mesmo assim.
SCHEMA = {
    "type": "object",
    "properties": {
        "interpretacao": {"type": "string"},
        "fatos_observados": {"type": "array", "items": {"type": "string"}},
        "acao": {"type": "string", "enum": ["executar", "finalizar"]},
        "ferramenta": {"type": "string", "enum": [*FERRAMENTAS, "nenhuma"]},
        "parametros": {"type": "object"},
        "justificativa": {"type": "string"},
        "conclusao": {"type": "string"},
    },
    "required": ["interpretacao", "fatos_observados", "acao", "ferramenta", "parametros", "justificativa", "conclusao"],
}


def _post(cfg: dict, rota: str, corpo: dict | None = None, timeout: int = 30) -> dict:
    url = cfg["modelo"]["url"].rstrip("/") + rota
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def info_modelo(cfg: dict) -> dict:
    """Digest e detalhes do modelo configurado, para registrar no log."""
    nome = cfg["modelo"]["nome"]
    try:
        tags = _post(cfg, "/api/tags")
        versao = _post(cfg, "/api/version").get("version")
    except (urllib.error.URLError, OSError) as erro:
        return {"nome": nome, "erro": str(erro)}
    for m in tags.get("models", []):
        if m.get("name") == nome or m.get("model") == nome:
            return {"nome": nome, "digest": m.get("digest"), "detalhes": m.get("details"), "ollama": versao}
    return {"nome": nome, "digest": None, "ollama": versao}


def validar_resposta(dados) -> list[str]:
    erros = []
    if not isinstance(dados, dict):
        return ["a resposta não é um objeto JSON"]
    for campo in SCHEMA["required"]:
        if campo not in dados:
            erros.append(f"campo ausente: {campo}")
    if erros:
        return erros
    for campo in ("interpretacao", "justificativa", "conclusao", "acao", "ferramenta"):
        if not isinstance(dados[campo], str):
            erros.append(f"{campo} deve ser texto")
    if not isinstance(dados["fatos_observados"], list) or not all(isinstance(f, str) for f in dados["fatos_observados"]):
        erros.append("fatos_observados deve ser uma lista de textos")
    if not isinstance(dados["parametros"], dict):
        erros.append("parametros deve ser um objeto")
    if dados.get("acao") not in ("executar", "finalizar"):
        erros.append("acao deve ser 'executar' ou 'finalizar'")
    if dados.get("acao") == "executar" and dados.get("ferramenta") not in FERRAMENTAS:
        erros.append(f"com acao 'executar', ferramenta deve ser uma de {list(FERRAMENTAS)}")
    if dados.get("acao") == "finalizar" and not str(dados.get("conclusao", "")).strip():
        erros.append("com acao 'finalizar', conclusao não pode ser vazia")
    return erros


def chamar(cfg: dict, mensagens: list[dict]) -> dict:
    """Uma chamada ao modelo. Devolve conteúdo bruto, dados (se válidos), erros e tempos."""
    m = cfg["modelo"]
    corpo = {
        "model": m["nome"],
        "messages": mensagens,
        "stream": False,
        "think": bool(m.get("think", False)),
        "format": SCHEMA,
        "options": {"temperature": m["temperature"], "seed": m["seed"], "num_ctx": m["num_ctx"]},
    }
    inicio = time.monotonic()
    try:
        resposta = _post(cfg, "/api/chat", corpo, timeout=int(m["timeout_s"]))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as erro:
        return {"bruto": "", "dados": None, "erros": [f"falha na chamada ao Ollama: {erro}"],
                "duracao_ms": int((time.monotonic() - inicio) * 1000), "metricas": {}}
    duracao = int((time.monotonic() - inicio) * 1000)
    mensagem = resposta.get("message", {})
    bruto = mensagem.get("content", "")
    metricas = {k: resposta.get(k) for k in ("prompt_eval_count", "eval_count", "total_duration", "eval_duration")}
    if mensagem.get("thinking"):
        metricas["thinking"] = mensagem["thinking"]

    texto = bruto.strip()
    if "</think>" in texto:  # caso o modelo ignore think=false
        texto = texto.split("</think>", 1)[1].strip()
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as erro:
        return {"bruto": bruto, "dados": None, "erros": [f"JSON inválido: {erro}"], "duracao_ms": duracao, "metricas": metricas}
    erros = validar_resposta(dados)
    return {"bruto": bruto, "dados": None if erros else dados, "erros": erros, "duracao_ms": duracao, "metricas": metricas}
