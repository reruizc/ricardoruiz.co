import io
import json
import unittest
from pathlib import Path

from concepthia_pilot import web


class FakeProvider:
    def draft(self, question, sources):
        return "Borrador de prueba sustentado en [S1]."


class BrokenProvider:
    def draft(self, question, sources):
        raise ConnectionResetError("conexión cortada")


def request(application, method, path, payload=b""):
    captured = {}
    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)
    body = b"".join(application({"REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_LENGTH": str(len(payload)), "wsgi.input": io.BytesIO(payload)}, start_response))
    return captured["status"], captured["headers"], body


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_provider = web.provider_from_env
        web.provider_from_env = lambda: FakeProvider()
        cls.app = web.app(Path("data"))

    @classmethod
    def tearDownClass(cls):
        web.provider_from_env = cls.original_provider

    def test_home_renders_question_form(self):
        status, _, body = request(type(self).app, "GET", "/")
        self.assertEqual(status, "200 OK")
        self.assertIn(b"Consultar fuentes", body)
        self.assertIn(b"textarea", body)
        self.assertIn(b"renderDraft", body)
        self.assertGreater(body.index(b"Datos del oficio"), body.index(b"Empezar a construir documento"))
        self.assertIn(b"concepthia.subdirector", body)

    def test_answer_returns_draft_and_sources(self):
        status, _, body = request(type(self).app, "POST", "/api/answer", json.dumps({"question": "¿Cómo aplica la prima técnica?"}).encode())
        data = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertIn("[S1]", data["answer"])
        self.assertGreaterEqual(len(data["sources"]), 1)
        self.assertIn("url_ficha", data["sources"][0])
        self.assertEqual(data["jurisprudence"], [])

    def test_jurisprudence_review_returns_official_searches(self):
        payload = json.dumps({"question": "prima técnica", "review_jurisprudence": True}).encode()
        status, _, body = request(type(self).app, "POST", "/api/answer", payload)
        data = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(len(data["jurisprudence"]), 2)
        self.assertTrue(all(link["url"].startswith("https://") for link in data["jurisprudence"]))

    def test_display_date_formats_iso_date_in_spanish(self):
        self.assertEqual(web.display_date("2026-08-22"), "22 de agosto de 2026")

    def test_answer_rejects_short_question(self):
        status, _, body = request(type(self).app, "POST", "/api/answer", b'{"question":"x"}')
        self.assertEqual(status, "400 Bad Request")
        self.assertIn("3 a 1.500", json.loads(body)["error"])

    def test_unexpected_provider_failure_returns_json_error(self):
        original_provider = web.provider_from_env
        web.provider_from_env = lambda: BrokenProvider()
        try:
            status, _, body = request(
                type(self).app,
                "POST",
                "/api/answer",
                json.dumps({"question": "¿Cómo aplica la prima técnica?"}).encode(),
            )
        finally:
            web.provider_from_env = original_provider
        self.assertEqual(status, "500 Internal Server Error")
        self.assertIn("Intenta nuevamente", json.loads(body)["error"])


if __name__ == "__main__":
    unittest.main()
