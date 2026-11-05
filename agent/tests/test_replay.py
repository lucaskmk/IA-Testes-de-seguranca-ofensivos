"""Testes da troca do bloco de evento usada pelo replay contrafactual."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import replay  # noqa: E402

MENSAGEM = ("OBJETIVO DA INVESTIGAÇÃO: x\n\nTURNO: 2 de 15\n\nFATOS ANOTADOS POR VOCÊ ATÉ AGORA (não verificados pelo humano):\n- a\n\n"
            "HISTÓRICO RECENTE:\nturno 1: ...\n\nÚLTIMO EVENTO:\nResultado do turno 1:\nHTTP/1.1 200 OK\n\n"
            "Responda com o objeto JSON pedido.")


class TestTrocarEvento(unittest.TestCase):
    def test_troca_so_o_evento(self):
        nova, original = replay.trocar_evento(MENSAGEM, "HTTP/1.1 401 Unauthorized")
        self.assertEqual(original, "Resultado do turno 1:\nHTTP/1.1 200 OK")
        self.assertIn("ÚLTIMO EVENTO:\nHTTP/1.1 401 Unauthorized\n\nResponda", nova)
        self.assertEqual(nova.split("ÚLTIMO EVENTO:")[0], MENSAGEM.split("ÚLTIMO EVENTO:")[0])

    def test_mensagem_sem_evento(self):
        with self.assertRaises(ValueError):
            replay.trocar_evento("sem marcadores", "x")


if __name__ == "__main__":
    unittest.main()
