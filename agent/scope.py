"""Trava de escopo: valida a proposta do modelo e monta o comando a executar.

O modelo nunca escolhe host nem porta: eles vêm da configuração. Aqui só se aceitam
ferramentas conhecidas, parâmetros com tipo e formato esperados e flags de uma lista
permitida. Qualquer desvio levanta ForaDeEscopo, que o agente registra no log.
"""

import re
from dataclasses import dataclass, field

FERRAMENTAS = ("http_request", "nmap_scan", "dir_enum", "decode_jwt")

METODOS_HTTP = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
FLAGS_NMAP = {"-sT", "-sV", "-Pn", "-n", "-T2", "-T3", "-T4", "--version-light", "--version-all", "--reason", "-v"}
WORDLISTS = {
    "dirb_small": "/usr/share/dirb/wordlists/small.txt",
    "dirb_common": "/usr/share/dirb/wordlists/common.txt",
}

# Caminho: começa com "/" e só tem ASCII imprimível sem espaço (bloqueia CR/LF e troca de host).
_RE_CAMINHO = re.compile(r"^/[\x21-\x7e]{0,2047}$")
_RE_NOME_CABECALHO = re.compile(r"^[A-Za-z0-9-]{1,64}$")
_RE_EXTENSAO = re.compile(r"^\.[A-Za-z0-9]{1,6}$")
_RE_JWT = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*$")
_RE_URL_EXTERNA = re.compile(r"https?://(?!juiceshop[:/]|juiceshop$)[^\s\"'<>]+", re.IGNORECASE)


class ForaDeEscopo(Exception):
    """Proposta recusada pela trava de escopo."""


@dataclass
class Comando:
    ferramenta: str
    parametros: dict
    argv: list[str] = field(default_factory=list)  # executado com docker exec no container do Kali
    stdin: bytes | None = None
    local: bool = False  # ferramentas sem rede, executadas no próprio agente
    avisos: list[str] = field(default_factory=list)


def _texto(params: dict, chave: str, obrigatorio: bool = True, padrao: str = "") -> str:
    valor = params.get(chave, None)
    if valor is None:
        if obrigatorio:
            raise ForaDeEscopo(f"parâmetro obrigatório ausente: {chave}")
        return padrao
    if not isinstance(valor, str):
        raise ForaDeEscopo(f"parâmetro {chave} deve ser texto")
    return valor


def _sem_quebra_de_linha(valor: str, nome: str) -> None:
    if "\r" in valor or "\n" in valor:
        raise ForaDeEscopo(f"{nome} contém quebra de linha")


def _urls_externas(*textos: str) -> list[str]:
    achadas = []
    for texto in textos:
        achadas.extend(_RE_URL_EXTERNA.findall(texto or ""))
    return achadas


def _caminho(valor: str) -> str:
    if not _RE_CAMINHO.match(valor):
        raise ForaDeEscopo("caminho deve começar com '/' e conter só ASCII imprimível sem espaços")
    return valor


def validar(ferramenta: str, params, cfg: dict) -> Comando:
    if ferramenta not in FERRAMENTAS:
        raise ForaDeEscopo(f"ferramenta desconhecida: {ferramenta!r}")
    if not isinstance(params, dict):
        raise ForaDeEscopo("parâmetros devem ser um objeto JSON")
    host, porta = cfg["alvo"]["host"], int(cfg["alvo"]["porta"])
    base = f"http://{host}:{porta}"
    lim = cfg["limites"]
    return {
        "http_request": _http_request,
        "nmap_scan": _nmap_scan,
        "dir_enum": _dir_enum,
        "decode_jwt": _decode_jwt,
    }[ferramenta](params, host, porta, base, lim)


def _http_request(params, host, porta, base, lim) -> Comando:
    permitidos = {"method", "path", "headers", "body"}
    extras = set(params) - permitidos
    if extras:
        raise ForaDeEscopo(f"parâmetros não aceitos em http_request: {sorted(extras)}")
    metodo = _texto(params, "method", padrao="GET", obrigatorio=False).upper() or "GET"
    if metodo not in METODOS_HTTP:
        raise ForaDeEscopo(f"método HTTP não permitido: {metodo}")
    caminho = _caminho(_texto(params, "path"))

    cabecalhos = params.get("headers") or {}
    if not isinstance(cabecalhos, dict) or len(cabecalhos) > 20:
        raise ForaDeEscopo("headers deve ser um objeto com no máximo 20 entradas")
    argv = ["curl", "-sS", "-i", "--path-as-is", "--proto", "=http",
            "--max-time", "30", "--max-filesize", "2000000"]
    argv += ["-I"] if metodo == "HEAD" else ["-X", metodo]
    for nome, valor in cabecalhos.items():
        if not isinstance(nome, str) or not _RE_NOME_CABECALHO.match(nome):
            raise ForaDeEscopo(f"nome de cabeçalho inválido: {nome!r}")
        if nome.lower() == "host":
            raise ForaDeEscopo("o cabeçalho Host não pode ser alterado")
        if not isinstance(valor, str) or len(valor) > 8192:
            raise ForaDeEscopo(f"valor do cabeçalho {nome} deve ser texto de até 8192 caracteres")
        _sem_quebra_de_linha(valor, f"cabeçalho {nome}")
        argv += ["-H", f"{nome}: {valor}"]

    corpo = params.get("body")
    stdin = None
    if corpo is not None:
        if isinstance(corpo, (dict, list)):
            import json
            corpo = json.dumps(corpo, ensure_ascii=False)
        if not isinstance(corpo, str):
            raise ForaDeEscopo("body deve ser texto ou JSON")
        stdin = corpo.encode("utf-8")
        if len(stdin) > int(lim["max_corpo_bytes"]):
            raise ForaDeEscopo(f"body maior que {lim['max_corpo_bytes']} bytes")
        argv += ["--data-binary", "@-"]  # corpo pela entrada padrão: "@arquivo" nunca é interpretado
    argv.append(base + caminho)

    avisos = []
    externas = _urls_externas(caminho, corpo or "", *[str(v) for v in cabecalhos.values()])
    if externas:
        avisos.append(f"URL externa nos parâmetros: {externas[:3]} (a rede labnet bloqueia, mas avalie antes de autorizar)")
    return Comando("http_request", {"method": metodo, "path": caminho, "headers": cabecalhos, "body": corpo},
                   argv=argv, stdin=stdin, avisos=avisos)


def _nmap_scan(params, host, porta, base, lim) -> Comando:
    extras = set(params) - {"flags"}
    if extras:
        raise ForaDeEscopo(f"parâmetros não aceitos em nmap_scan: {sorted(extras)} (alvo e porta são fixos)")
    flags = params.get("flags") or []
    if isinstance(flags, str):
        flags = flags.split()
    if not isinstance(flags, list) or not all(isinstance(f, str) for f in flags):
        raise ForaDeEscopo("flags deve ser uma lista de textos")
    proibidas = [f for f in flags if f not in FLAGS_NMAP]
    if proibidas:
        raise ForaDeEscopo(f"flags fora da lista permitida: {proibidas}; permitidas: {sorted(FLAGS_NMAP)}")
    argv = ["nmap", *flags, "-p", str(porta), host]
    return Comando("nmap_scan", {"flags": flags}, argv=argv)


def _dir_enum(params, host, porta, base, lim) -> Comando:
    permitidos = {"path_base", "wordlist", "extensoes", "filtrar_tamanhos", "filtrar_codigos", "autocalibrar"}
    extras = set(params) - permitidos
    if extras:
        raise ForaDeEscopo(f"parâmetros não aceitos em dir_enum: {sorted(extras)}")
    base_caminho = _caminho(_texto(params, "path_base", obrigatorio=False, padrao="/") or "/")
    if not base_caminho.endswith("/"):
        base_caminho += "/"
    lista = _texto(params, "wordlist", obrigatorio=False, padrao="dirb_small") or "dirb_small"
    if lista not in WORDLISTS:
        raise ForaDeEscopo(f"wordlist desconhecida: {lista}; disponíveis: {sorted(WORDLISTS)}")

    argv = ["ffuf", "-u", f"{base}{base_caminho}FUZZ", "-w", WORDLISTS[lista],
            "-rate", "50", "-t", "10", "-mc", "all", "-json", "-noninteractive", "-maxtime", "240"]

    extensoes = params.get("extensoes") or []
    if not isinstance(extensoes, list) or len(extensoes) > 3 or not all(isinstance(e, str) and _RE_EXTENSAO.match(e) for e in extensoes):
        raise ForaDeEscopo("extensoes: lista de até 3 itens no formato '.ext'")
    if extensoes:
        argv += ["-e", ",".join(extensoes)]

    for chave, opcao in (("filtrar_tamanhos", "-fs"), ("filtrar_codigos", "-fc")):
        valores = params.get(chave) or []
        if not isinstance(valores, list) or len(valores) > 10 or not all(isinstance(v, int) and v >= 0 for v in valores):
            raise ForaDeEscopo(f"{chave}: lista de até 10 inteiros")
        if valores:
            argv += [opcao, ",".join(str(v) for v in valores)]

    autocalibrar = params.get("autocalibrar", False)
    if not isinstance(autocalibrar, bool):
        raise ForaDeEscopo("autocalibrar deve ser true ou false")
    if autocalibrar:
        argv.append("-ac")

    normalizados = {"path_base": base_caminho, "wordlist": lista, "extensoes": extensoes,
                    "filtrar_tamanhos": params.get("filtrar_tamanhos") or [],
                    "filtrar_codigos": params.get("filtrar_codigos") or [], "autocalibrar": autocalibrar}
    return Comando("dir_enum", normalizados, argv=argv)


def _decode_jwt(params, host, porta, base, lim) -> Comando:
    extras = set(params) - {"token"}
    if extras:
        raise ForaDeEscopo(f"parâmetros não aceitos em decode_jwt: {sorted(extras)}")
    token = _texto(params, "token").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if len(token) > 8192 or not _RE_JWT.match(token):
        raise ForaDeEscopo("token não tem o formato header.payload.assinatura em base64url")
    return Comando("decode_jwt", {"token": token}, local=True)
