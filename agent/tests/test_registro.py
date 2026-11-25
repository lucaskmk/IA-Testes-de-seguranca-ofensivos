"""Testes do que vai para o log: fatos do modelo, tags, versão do código e integridade das saídas."""

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agent  # noqa: E402
import proveniencia  # noqa: E402
import summarize_logs  # noqa: E402


class TestFatos(unittest.TestCase):
    def test_diferenca(self):
        adicionados, removidos = agent.diferenca_fatos(["a", "b"], ["b", "c"])
        self.assertEqual(adicionados, ["c"])
        self.assertEqual(removidos, ["a"])

    def test_sem_mudanca(self):
        self.assertEqual(agent.diferenca_fatos(["a"], ["a"]), ([], []))
        self.assertEqual(agent._texto_fatos([], []), "(sem mudanças)")


class TestTags(unittest.TestCase):
    def test_tag_fora_da_lista_pede_de_novo(self):
        with mock.patch("builtins.input", side_effect=["alucinação", "alucinacao, repeticao"]), \
             mock.patch("builtins.print"):
            self.assertEqual(agent.perguntar_tags(), ["alucinacao", "repeticao"])

    def test_vazio(self):
        with mock.patch("builtins.input", return_value=""):
            self.assertEqual(agent.perguntar_tags(), [])


class TestProveniencia(unittest.TestCase):
    def test_hash_do_conjunto_muda_com_o_codigo(self):
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            (raiz / "agent" / "prompts").mkdir(parents=True)
            (raiz / "agent" / "a.py").write_text("x = 1\n")
            (raiz / "agent" / "prompts" / "s.md").write_text("prompt\n")
            antes = proveniencia.hash_arquivos(raiz)
            self.assertEqual(sorted(antes["arquivos"]), ["agent/a.py", "agent/prompts/s.md"])
            (raiz / "agent" / "a.py").write_text("x = 2\n")
            self.assertNotEqual(antes["sha256_conjunto"], proveniencia.hash_arquivos(raiz)["sha256_conjunto"])


class TestIntegridade(unittest.TestCase):
    def test_confere_e_acusa_diferenca(self):
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            (raiz / "logs" / "raw").mkdir(parents=True)
            (raiz / "logs" / "raw" / "ok.txt").write_bytes(b"saida")
            (raiz / "logs" / "raw" / "alterado.txt").write_bytes(b"editado")
            registros = [
                {"turno": 1, "saida_arquivo": "logs/raw/ok.txt", "saida_sha256": hashlib.sha256(b"saida").hexdigest()},
                {"turno": 2, "saida_arquivo": "logs/raw/alterado.txt", "saida_sha256": hashlib.sha256(b"original").hexdigest()},
                {"turno": 3, "saida_arquivo": "logs/raw/sumiu.txt", "saida_sha256": "x"},
                {"turno": 4, "decisao_humana": "REJEITADO"},
            ]
            conferidas, problemas = summarize_logs.verificar_integridade(registros, raiz)
            self.assertEqual(conferidas, 2)
            self.assertEqual(len(problemas), 2)
            self.assertIn("turno 2", problemas[0])
            self.assertIn("turno 3", problemas[1])


if __name__ == "__main__":
    unittest.main()
