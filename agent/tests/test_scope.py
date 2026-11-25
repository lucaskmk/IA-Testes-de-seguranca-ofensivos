"""Testes da trava de escopo. Rodar na raiz: python3 -m unittest discover -s agent/tests -v"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
import scope  # noqa: E402
from scope import ForaDeEscopo  # noqa: E402

CFG = config.carregar()


class TestHttpRequest(unittest.TestCase):
    def test_get_simples_vai_para_o_alvo_fixo(self):
        cmd = scope.validar("http_request", {"method": "GET", "path": "/"}, CFG)
        self.assertEqual(cmd.argv[-1], "http://juiceshop:3000/")
        self.assertNotIn("-L", cmd.argv)

    def test_host_nao_pode_ser_trocado_pelo_caminho(self):
        for caminho in ("http://example.com/", "example.com", "", " /espaco", "/a\r\nHost: x"):
            with self.subTest(caminho=caminho):
                with self.assertRaises(ForaDeEscopo):
                    scope.validar("http_request", {"path": caminho}, CFG)

    def test_arroba_no_caminho_continua_no_alvo(self):
        cmd = scope.validar("http_request", {"path": "/@example.com"}, CFG)
        self.assertTrue(cmd.argv[-1].startswith("http://juiceshop:3000/"))

    def test_parametros_de_host_ou_porta_sao_recusados(self):
        for extra in ({"host": "10.0.80.1"}, {"url": "http://1.1.1.1"}, {"port": 22}):
            with self.subTest(extra=extra):
                with self.assertRaises(ForaDeEscopo):
                    scope.validar("http_request", {"path": "/", **extra}, CFG)

    def test_cabecalho_host_e_quebra_de_linha_recusados(self):
        with self.assertRaises(ForaDeEscopo):
            scope.validar("http_request", {"path": "/", "headers": {"Host": "example.com"}}, CFG)
        with self.assertRaises(ForaDeEscopo):
            scope.validar("http_request", {"path": "/", "headers": {"X-A": "1\r\nX-B: 2"}}, CFG)

    def test_corpo_vai_pela_entrada_padrao(self):
        cmd = scope.validar("http_request", {"method": "POST", "path": "/x", "body": "@/etc/passwd"}, CFG)
        self.assertIn("@-", cmd.argv)
        self.assertEqual(cmd.stdin, b"@/etc/passwd")

    def test_corpo_json_e_serializado(self):
        cmd = scope.validar("http_request", {"method": "POST", "path": "/x", "body": {"a": 1}}, CFG)
        self.assertEqual(cmd.stdin, b'{"a": 1}')

    def test_url_externa_gera_aviso(self):
        cmd = scope.validar("http_request", {"path": "/r?to=https://example.com"}, CFG)
        self.assertTrue(cmd.avisos)
        cmd = scope.validar("http_request", {"path": "/r?to=http://juiceshop:3000/x"}, CFG)
        self.assertFalse(cmd.avisos)

    def test_metodo_desconhecido(self):
        with self.assertRaises(ForaDeEscopo):
            scope.validar("http_request", {"method": "TRACE", "path": "/"}, CFG)


class TestNmap(unittest.TestCase):
    def test_alvo_e_porta_fixos(self):
        cmd = scope.validar("nmap_scan", {"flags": ["-sT", "-sV"]}, CFG)
        self.assertEqual(cmd.argv[-3:], ["-p", "3000", "juiceshop"])

    def test_flags_fora_da_lista(self):
        for flags in (["--script", "vuln"], ["-p-"], ["10.0.80.1"], ["-sS"], ["-iL", "/etc/hosts"]):
            with self.subTest(flags=flags):
                with self.assertRaises(ForaDeEscopo):
                    scope.validar("nmap_scan", {"flags": flags}, CFG)

    def test_alvo_ou_porta_como_parametro(self):
        with self.assertRaises(ForaDeEscopo):
            scope.validar("nmap_scan", {"flags": ["-sT"], "target": "10.0.80.3"}, CFG)
        with self.assertRaises(ForaDeEscopo):
            scope.validar("nmap_scan", {"flags": ["-sT"], "ports": "22,11434"}, CFG)


class TestDirEnum(unittest.TestCase):
    def test_padrao(self):
        cmd = scope.validar("dir_enum", {}, CFG)
        self.assertIn("http://juiceshop:3000/FUZZ", cmd.argv)
        self.assertNotIn("-ac", cmd.argv)

    def test_wordlist_arbitraria_recusada(self):
        with self.assertRaises(ForaDeEscopo):
            scope.validar("dir_enum", {"wordlist": "/etc/passwd"}, CFG)

    def test_filtros(self):
        cmd = scope.validar("dir_enum", {"filtrar_tamanhos": [123], "autocalibrar": True}, CFG)
        self.assertIn("-fs", cmd.argv)
        self.assertIn("-ac", cmd.argv)
        with self.assertRaises(ForaDeEscopo):
            scope.validar("dir_enum", {"filtrar_tamanhos": ["123; rm"]}, CFG)


class TestOutros(unittest.TestCase):
    def test_ferramenta_desconhecida(self):
        for nome in ("shell", "bash", "sqlmap", ""):
            with self.subTest(nome=nome):
                with self.assertRaises(ForaDeEscopo):
                    scope.validar(nome, {}, CFG)

    def test_jwt(self):
        cmd = scope.validar("decode_jwt", {"token": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhIjoxfQ.c2ln"}, CFG)
        self.assertTrue(cmd.local)
        with self.assertRaises(ForaDeEscopo):
            scope.validar("decode_jwt", {"token": "não é jwt"}, CFG)


if __name__ == "__main__":
    unittest.main()
