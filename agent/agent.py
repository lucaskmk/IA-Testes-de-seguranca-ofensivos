#!/usr/bin/env python3
"""Agente supervisionado: o modelo propõe, o grupo decide, a ferramenta executa, o modelo interpreta.

Uso (na raiz do repositório, dentro do tmux no servidor):
    python3 agent/agent.py --id I1 --objetivo "..." --restore

Cada proposta passa por [a]utorizar, [m]odificar, [r]ejeitar ou [f]inalizar. Tudo é gravado
em logs/ a cada turno (ver logger.py).
"""

import argparse
import json
import subprocess
import sys

import config as configuracao
import llm
import scope
import tools
from logger import Registro, sha256

DECISOES = {"a": "AUTORIZADO", "m": "MODIFICADO", "r": "REJEITADO", "f": "FINALIZADO"}
CLASSIFICACOES = {"c": "CONFIRMADA", "r": "REFUTADA", "i": "INCONCLUSIVA"}


def perguntar(texto: str, obrigatorio: bool = False, opcoes: list[str] | None = None) -> str:
    while True:
        try:
            resposta = input(texto).strip()
        except EOFError:
            print()
            sys.exit("Entrada encerrada; o log contém tudo até o último turno gravado.")
        if opcoes and resposta.lower() not in opcoes:
            print(f"  opções: {' / '.join(opcoes)}")
            continue
        if obrigatorio and not resposta:
            print("  campo obrigatório.")
            continue
        return resposta.lower() if opcoes else resposta


def mostrar(titulo: str, texto: str) -> None:
    print(f"\n=== {titulo} ===\n{texto}", flush=True)


def _json(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, sort_keys=True)


def _inspecionar_imagem(container: str) -> str | None:
    proc = subprocess.run(["docker", "inspect", container, "--format", "{{.Config.Image}} {{.Image}}"],
                          capture_output=True, text=True)
    return proc.stdout.strip() or None


class Agente:
    def __init__(self, cfg: dict, registro: Registro, objetivo: str):
        self.cfg = cfg
        self.reg = registro
        self.objetivo = objetivo
        self.sistema = cfg["caminhos"]["prompt_sistema"].read_text(encoding="utf-8")
        self.fatos: list[str] = []
        self.historico: list[str] = []
        self.propostas_anteriores: dict[str, int] = {}
        self.turno = 0
        m = cfg["modelo"]
        self.config_log = {
            "modelo": llm.info_modelo(cfg),
            "temperature": m["temperature"], "seed": m["seed"], "num_ctx": m["num_ctx"], "think": m["think"],
            "prompt_sistema_sha256": sha256(self.sistema),
            "arquivo_config": cfg["_arquivo"],
            "alvo": f"{cfg['alvo']['host']}:{cfg['alvo']['porta']}",
            "juiceshop": _inspecionar_imagem("juiceshop"),
            "kali": _inspecionar_imagem(cfg["alvo"]["container"]),
        }

    # ---------- modelo ----------

    def _mensagem_usuario(self, evento: str) -> str:
        lim = self.cfg["limites"]
        fatos = "\n".join(f"- {f}" for f in self.fatos) or "- (nenhum)"
        historico = "\n".join(self.historico[-int(lim["historico_turnos"]):]) or "(nenhum turno anterior)"
        return (f"OBJETIVO DA INVESTIGAÇÃO: {self.objetivo}\n\n"
                f"TURNO: {self.turno + 1} de {lim['max_turnos']}\n\n"
                f"FATOS OBSERVADOS ATÉ AGORA:\n{fatos}\n\n"
                f"HISTÓRICO RECENTE:\n{historico}\n\n"
                f"ÚLTIMO EVENTO:\n{evento}\n\n"
                "Responda com o objeto JSON pedido.")

    def consultar(self, evento: str) -> tuple[dict | None, list[str], int]:
        """Pede ao modelo interpretação + próxima ação. Uma nova tentativa se o JSON vier inválido."""
        mensagens = [{"role": "system", "content": self.sistema},
                     {"role": "user", "content": self._mensagem_usuario(evento)}]
        ids = []
        for tentativa in (1, 2):
            print("\n[consultando o modelo...]", flush=True)
            res = llm.chamar(self.cfg, mensagens)
            ids.append(self.reg.chamada_modelo(mensagens, res, tentativa))
            print(f"[resposta em {res['duracao_ms'] / 1000:.1f} s]", flush=True)
            if res["dados"] is not None:
                return res["dados"], ids, tentativa
            print(f"[resposta inválida: {'; '.join(res['erros'])}]")
            mensagens = mensagens + [
                {"role": "assistant", "content": res["bruto"]},
                {"role": "user", "content": "A resposta anterior não seguiu o formato: " + "; ".join(res["erros"])
                 + ". Responda novamente apenas com o objeto JSON pedido."},
            ]
        return None, ids, 2

    # ---------- interação ----------

    def _mostrar_proposta(self, p: dict, bloqueio: str | None, avisos: list[str], repete: int | None) -> None:
        texto = (f"Ação: {p['acao']}\nFerramenta: {p['ferramenta']}\n"
                 f"Parâmetros: {_json(p['parametros'])}\nJustificativa: {p['justificativa']}")
        if p["acao"] == "finalizar":
            texto += f"\nConclusão proposta: {p['conclusao']}"
        mostrar(f"Turno {self.turno} · proposta do modelo", texto)
        if repete:
            print(f"[atenção: proposta idêntica à do turno {repete}]")
        for aviso in avisos:
            print(f"[aviso: {aviso}]")
        if bloqueio:
            print(f"[BLOQUEADO pela trava de escopo: {bloqueio}]")

    def _modificar(self, ferramenta: str, params: dict) -> scope.Comando | None:
        print(f"Atual: {ferramenta} {_json(params)}")
        while True:
            nova = perguntar(f"Ferramenta [{ferramenta}]: ") or ferramenta
            texto = perguntar("Parâmetros em JSON numa linha (Enter mantém os atuais): ")
            try:
                novos = json.loads(texto) if texto else params
                return scope.validar(nova, novos, self.cfg)
            except json.JSONDecodeError as erro:
                print(f"[JSON inválido: {erro}]")
            except scope.ForaDeEscopo as erro:
                print(f"[fora de escopo: {erro}]")
            if perguntar("Tentar outra modificação? [s/n] ", opcoes=["s", "n"]) == "n":
                return None

    def _encerrar(self, conclusao_modelo: str | None, motivo: str) -> None:
        if conclusao_modelo:
            mostrar("Conclusão proposta pelo modelo", conclusao_modelo)
        print("\nEncerramento da investigação (preenchido pelo grupo).")
        classe = CLASSIFICACOES[perguntar("Conclusão do grupo: [c]onfirmada / [r]efutada / [i]nconclusiva: ",
                                          opcoes=list(CLASSIFICACOES))]
        afirmacao = perguntar("O que as evidências permitem afirmar (cite os turnos): ", obrigatorio=True)
        limitacoes = perguntar("Limitações que permanecem: ", obrigatorio=True)
        self.reg.turno({"tipo": "encerramento", "turnos": self.turno, "motivo": motivo,
                        "conclusao_modelo": conclusao_modelo, "classificacao": classe,
                        "conclusao_grupo": afirmacao, "limitacoes": limitacoes,
                        "fatos_observados_finais": self.fatos})
        print(f"\nInvestigação encerrada: {classe}. Log: {self.reg.arq_turnos}")

    # ---------- laço principal ----------

    def executar(self) -> None:
        lim = self.cfg["limites"]
        evento = "Início da investigação. Nenhuma ação executada ainda."
        proposta, ids, tentativas = self.consultar(evento)

        while True:
            if proposta is None:
                if perguntar("O modelo não produziu JSON válido. [t]entar de novo ou [f]inalizar? ", opcoes=["t", "f"]) == "t":
                    proposta, ids, tentativas = self.consultar(evento)
                    continue
                self._encerrar(None, "modelo sem resposta válida")
                return

            self.turno += 1
            self.fatos = [str(f) for f in proposta["fatos_observados"]][: int(lim["max_fatos"])]
            chave = f"{proposta['ferramenta']} {_json(proposta['parametros'])}"
            repete = self.propostas_anteriores.get(chave) if proposta["acao"] == "executar" else None
            self.propostas_anteriores.setdefault(chave, self.turno)

            cmd, bloqueio, avisos = None, None, []
            if proposta["acao"] == "executar":
                try:
                    cmd = scope.validar(proposta["ferramenta"], proposta["parametros"], self.cfg)
                    avisos = cmd.avisos
                except scope.ForaDeEscopo as erro:
                    bloqueio = str(erro)

            reg = {"tipo": "turno", "turno": self.turno, "objetivo": self.objetivo, "config": self.config_log,
                   "chamadas_modelo": ids, "json_valido_primeira_tentativa": tentativas == 1, "tentativas": tentativas,
                   "acao_proposta": proposta["acao"], "ferramenta_proposta": proposta["ferramenta"],
                   "parametros_propostos": proposta["parametros"], "justificativa_modelo": proposta["justificativa"],
                   "conclusao_proposta": proposta["conclusao"] or None, "repete_turno": repete,
                   "bloqueio_escopo": bloqueio, "avisos_escopo": avisos}
            self._mostrar_proposta(proposta, bloqueio, avisos, repete)

            if self.turno >= int(lim["max_turnos"]):
                print(f"[limite de {lim['max_turnos']} turnos atingido: só é possível finalizar]")
                opcoes = ["f"]
            elif proposta["acao"] == "finalizar":
                opcoes = ["f", "r"]
            elif bloqueio:
                opcoes = ["m", "r", "f"]
            else:
                opcoes = ["a", "m", "r", "f"]
            nomes = {"a": "[a]utorizar", "m": "[m]odificar", "r": "[r]ejeitar", "f": "[f]inalizar"}
            letra = perguntar("Decisão " + " / ".join(nomes[o] for o in opcoes) + ": ", opcoes=opcoes)
            motivo = perguntar("Justificativa da decisão: ", obrigatorio=True)

            if letra == "m":
                cmd = self._modificar(proposta["ferramenta"], proposta["parametros"])
                if cmd is None:
                    letra = "r"
                    motivo += " (modificação abandonada)"

            if letra == "f":
                reg.update({"decisao_humana": DECISOES["f"], "motivo_decisao": motivo})
                self.reg.turno(reg)
                self._encerrar(proposta["conclusao"] or None, motivo)
                return

            if letra == "r":
                tags = ["fora_escopo"] if bloqueio else []
                extra = perguntar("Tags (vírgula, Enter = nenhuma): ")
                tags += [t.strip() for t in extra.split(",") if t.strip()]
                reg.update({"decisao_humana": DECISOES["r"], "motivo_decisao": motivo, "tags": tags})
                self.reg.turno(reg)
                self.historico.append(f"turno {self.turno}: {chave} -> REJEITADO. Motivo: {motivo}")
                evento = (f"O humano REJEITOU a proposta do turno {self.turno} ({chave}). Motivo: {motivo}"
                          + (f"\nBloqueio da trava de escopo: {bloqueio}" if bloqueio else ""))
                proposta, ids, tentativas = self.consultar(evento)
                continue

            # Autorizado ou modificado: executa.
            for aviso in cmd.avisos if letra == "m" else []:
                print(f"[aviso: {aviso}]")
            print(f"\n[executando {cmd.ferramenta}...]", flush=True)
            saida, codigo, duracao = tools.executar(cmd, self.cfg)
            arquivo, hash_saida = self.reg.saida_bruta(self.turno, saida)
            resumo = tools.resumir(cmd.ferramenta, saida, codigo, int(lim["max_chars_resumo"]))
            mostrar(f"Turno {self.turno} · resultado (resumo enviado ao modelo)", resumo)

            executado = f"{cmd.ferramenta} {_json(cmd.parametros)}"
            if letra == "m":
                evento = (f"O humano MODIFICOU a proposta do turno {self.turno}. Motivo: {motivo}\n"
                          f"Executado: {executado}\nResultado:\n{resumo}")
            else:
                evento = f"Resultado do turno {self.turno} ({executado}):\n{resumo}"
            proxima, ids_prox, tent_prox = self.consultar(evento)
            interpretacao = proxima["interpretacao"] if proxima else None
            mostrar(f"Turno {self.turno} · interpretação do modelo", interpretacao or "(sem resposta válida)")

            decisao_grupo = perguntar("Decisão do grupo após o resultado (o que a evidência mostra; a interpretação está correta?): ",
                                      obrigatorio=True)
            nova_hipotese = perguntar("Nova hipótese (Enter = nenhuma): ") or None
            tags = [t.strip() for t in perguntar("Tags (vírgula, Enter = nenhuma): ").split(",") if t.strip()]

            reg.update({
                "decisao_humana": DECISOES[letra], "motivo_decisao": motivo,
                "parametros_executados": cmd.parametros,
                "comando_executado": None if cmd.local else ["docker", "exec", "-i", self.cfg["alvo"]["container"], *cmd.argv],
                "codigo_saida": codigo, "saida_resumo": resumo, "saida_arquivo": arquivo, "saida_sha256": hash_saida,
                "duracao_ferramenta_ms": duracao, "interpretacao_modelo": interpretacao,
                "chamadas_interpretacao": ids_prox, "decisao_grupo_pos_resultado": decisao_grupo,
                "nova_hipotese": nova_hipotese, "tags": tags,
            })
            self.reg.turno(reg)
            self.historico.append(f"turno {self.turno}: {executado} -> {DECISOES[letra]} -> {tools.linha_curta(cmd.ferramenta, saida)}")
            proposta, ids, tentativas = proxima, ids_prox, tent_prox


def restaurar(cfg: dict, reg: Registro) -> bool:
    print("[executando restore do Juice Shop...]", flush=True)
    proc = subprocess.run(["bash", str(cfg["caminhos"]["restore"])], capture_output=True, text=True)
    ok = proc.returncode == 0
    reg.turno({"tipo": "restore", "status": "OK" if ok else "ERRO", "saida": proc.stdout + proc.stderr})
    print(proc.stdout + proc.stderr)
    return ok


def main() -> None:
    ap = argparse.ArgumentParser(description="Agente supervisionado contra o Juice Shop do laboratório")
    ap.add_argument("--id", required=True, help="identificador da investigação (ex.: I1, P0)")
    ap.add_argument("--objetivo", required=True, help="objetivo entregue ao modelo (sem a hipótese do grupo)")
    ap.add_argument("--restore", action="store_true", help="executa lab/restore.sh antes de começar")
    ap.add_argument("--config", help="arquivo TOML alternativo")
    args = ap.parse_args()

    cfg = configuracao.carregar(args.config)
    reg = Registro(cfg["caminhos"]["logs"], args.id)
    if args.restore and not restaurar(cfg, reg):
        sys.exit("Restore falhou; investigação não iniciada.")
    agente = Agente(cfg, reg, args.objetivo)
    reg.turno({"tipo": "inicio", "objetivo": args.objetivo, "restore_nesta_sessao": args.restore,
               "config": agente.config_log, "prompt_sistema": agente.sistema})
    print(f"Sessão {reg.sessao} · modelo {agente.config_log['modelo'].get('nome')} · alvo {agente.config_log['alvo']}")
    try:
        agente.executar()
    except KeyboardInterrupt:
        reg.turno({"tipo": "interrompido", "turnos": agente.turno})
        sys.exit("\nInterrompido; o log contém tudo até o último turno gravado.")


if __name__ == "__main__":
    main()
