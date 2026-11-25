"""De onde veio cada log: versão do código do agente e situação do plano no git.

O hash dos arquivos funciona mesmo numa cópia sem git (sincronizada por tar): basta
recalcular o mesmo hash a partir de um commit para saber qual código gerou o log.
"""

import hashlib
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVOS_CODIGO = ("agent/*.py", "agent/prompts/*.md", "agent/config.example.toml")


def _git(*args: str) -> str | None:
    try:
        proc = subprocess.run(["git", *args], capture_output=True, text=True, cwd=RAIZ)
    except OSError:
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def hash_arquivos(raiz: Path = RAIZ) -> dict:
    """SHA-256 de cada arquivo do agente e um hash único do conjunto."""
    arquivos = sorted({p for padrao in ARQUIVOS_CODIGO for p in raiz.glob(padrao)})
    por_arquivo = {p.relative_to(raiz).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}
    conjunto = "".join(f"{nome}:{h}\n" for nome, h in por_arquivo.items())
    return {"sha256_conjunto": hashlib.sha256(conjunto.encode()).hexdigest(), "arquivos": por_arquivo}


def versao_codigo() -> dict:
    """Commit, alterações não commitadas em agent/ e hashes dos arquivos do agente."""
    head = _git("rev-parse", "HEAD")
    sujo = None if head is None else bool(_git("status", "--porcelain", "--", "agent"))
    return {"git_head": head, "agent_com_alteracoes_nao_commitadas": sujo, **hash_arquivos()}


def verificar_plano(plano: Path) -> tuple[str | None, list[str]]:
    """Confere que o plano está commitado, sem alterações locais e no remoto. Devolve (commit, erros)."""
    if _git("rev-parse", "--is-inside-work-tree") != "true":
        return None, ["esta cópia não é um repositório git; no servidor, use git clone/git pull em vez de tar"]
    caminho = plano.relative_to(RAIZ).as_posix()
    commit = _git("log", "-1", "--format=%H %cI", "--", caminho)
    if not commit:
        return None, ["o plano não está commitado"]
    erros = []
    if _git("status", "--porcelain", "--", caminho):
        erros.append("o plano tem alterações não commitadas; o texto enviado não seria o do commit")
    if not _git("branch", "-r", "--contains", commit.split()[0]):
        erros.append("o commit do plano não está em nenhum branch remoto (faça git push e, no servidor, git pull)")
    return commit, erros
