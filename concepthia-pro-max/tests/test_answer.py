import os
import unittest
from unittest.mock import patch

from concepthia_pilot.answer import DeepSeekChatProvider, OpenAIResponsesProvider, make_sources, provider_from_env


class FakeChunk:
    chunk_id = "c1"
    radicado = "2-2023-3150"
    titulo = "Concepto"
    pagina = 1
    url_ficha = "https://example.test/ficha"
    url_pdf = "https://example.test/doc.pdf"
    texto = "Texto de prueba"


class FakeResult:
    score = 1.0
    chunk = FakeChunk()


class ProviderSelectionTests(unittest.TestCase):
    def test_sources_prefer_official_filing_number_as_citation(self):
        source = make_sources([FakeResult()])[0]
        self.assertEqual(source["id"], "Nro. Rad: 2-2023-3150")
        self.assertEqual(source["radicado"], "2-2023-3150")

    def test_deepseek_key_is_selected_automatically(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "deep-key", "OPENAI_API_KEY": "old-key"}, clear=True):
            self.assertIsInstance(provider_from_env(), DeepSeekChatProvider)

    def test_explicit_openai_selection(self):
        env = {"CONCEPTHIA_LLM_PROVIDER": "openai", "OPENAI_API_KEY": "open-key"}
        with patch.dict(os.environ, env, clear=True):
            self.assertIsInstance(provider_from_env(), OpenAIResponsesProvider)

    def test_missing_key_has_clear_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Falta una clave"):
                provider_from_env()


if __name__ == "__main__":
    unittest.main()
