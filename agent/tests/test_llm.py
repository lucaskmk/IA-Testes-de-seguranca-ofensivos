"""Testes da validação das respostas do modelo e do resumo das saídas."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import llm  # noqa: E402
import tools  # noqa: E402

VALIDA = {"interpretacao": "x", "fatos_observados": ["a"], "acao": "executar", "ferramenta": "http_request",
          "parametros": {"path": "/"}, "justificativa": "y", "conclusao": ""}


class TestValidacao(unittest.TestCase):
    def test_resposta_valida(self):
        self.assertEqual(llm.validar_resposta(VALIDA), [])

    def test_campo_ausente(self):
        dados = dict(VALIDA)
        del dados["justificativa"]
        self.assertTrue(llm.validar_resposta(dados))

    def test_executar_sem_ferramenta(self):
        self.assertTrue(llm.validar_resposta({**VALIDA, "ferramenta": "nenhuma"}))

    def test_finalizar_sem_conclusao(self):
        self.assertTrue(llm.validar_resposta({**VALIDA, "acao": "finalizar", "ferramenta": "nenhuma"}))

    def test_tipos(self):
        self.assertTrue(llm.validar_resposta({**VALIDA, "fatos_observados": "a"}))
        self.assertTrue(llm.validar_resposta({**VALIDA, "parametros": []}))
        self.assertTrue(llm.validar_resposta([]))


class TestResumo(unittest.TestCase):
    def test_truncamento(self):
        texto = "a" * 10000
        resumo = tools.resumir("http_request", texto, 0, 1000)
        self.assertLess(len(resumo), 1200)
        self.assertIn("omitidos", resumo)

    def test_ffuf_agrupa_por_status_e_tamanho(self):
        linhas = [json.dumps({"input": {"FUZZ": f"p{i}"}, "status": 200, "length": 3748, "words": 10}) for i in range(50)]
        linhas.append(json.dumps({"input": {"FUZZ": "raro"}, "status": 403, "length": 12, "words": 1}))
        resumo = tools.resumir("dir_enum", "\n".join(linhas), 0, 3000)
        self.assertIn("51 respostas", resumo)
        self.assertIn("/raro", resumo)
        self.assertNotIn("/p3 ", resumo)

    def test_jwt_local(self):
        saida = tools._decode_jwt("eyJhbGciOiJIUzI1NiJ9.eyJhIjoxfQ.c2ln")
        self.assertIn('"alg": "HS256"', saida)
        self.assertIn('"a": 1', saida)


if __name__ == "__main__":
    unittest.main()
