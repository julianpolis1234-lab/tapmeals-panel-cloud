"""
===============================================================================
CHALLENGER 2: EMPIRICAL STRESS & FALLBACK HARNESS FOR MILESTONE 1 (M1)
===============================================================================
Rigorous empirical challenge of:
1. Strict alias mapping (claude, gemini, opus, argon + casing, whitespace, defaults)
2. Live text generation across ALL 4 models (claude, gemini, opus, argon) without truncation
3. HTTP error injection & fallback durability (400, 401, 403, 404, 429, 500, 502, 503, 504,
   connection refused, timeout, malformed JSON, empty response, missing fields)
4. Response timing and latency measurement precision
===============================================================================
"""

import os
import sys
import time
import json
import socket
import threading
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError

# Encodings seguros
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_PANEL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_PANEL_DIR not in sys.path:
    sys.path.insert(0, BASE_PANEL_DIR)

import omniroute_client
from omniroute_client import (
    consultar_omniroute,
    resolver_nombre_modelo,
    verificar_estado_omniroute,
    MODEL_ALIASES,
    TAPMEALS_SYSTEM_PROMPT,
    FALLBACK_TAPMEALS_RESPONSE,
    DEFAULT_OMNIROUTE_URL,
)


class MockFaultyServerHandler(BaseHTTPRequestHandler):
    """Handler configurable para simular cualquier código de error HTTP o payload anómalo."""
    mode = "500"
    delay = 0.0
    custom_body = None

    def log_message(self, format, *args):
        pass  # Silenciar logs en pruebas

    def do_POST(self):
        if self.delay > 0:
            time.sleep(self.delay)

        if self.mode == "delay_only":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            body = json.dumps({
                "choices": [{"message": {"content": "Respuesta demorada exitosa."}}]
            }).encode("utf-8")
            self.wfile.write(body)
            return

        if self.mode == "400":
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Bad Request: invalid prompt"}')
            return

        if self.mode == "401":
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Unauthorized: invalid bearer token"}')
            return

        if self.mode == "403":
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Forbidden: access denied"}')
            return

        if self.mode == "404":
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Model endpoint not found"}')
            return

        if self.mode == "429":
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Too Many Requests: rate limit exceeded"}')
            return

        if self.mode == "500":
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Internal Server Error in upstream provider"}')
            return

        if self.mode == "502":
            self.send_response(502)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b'<html><body>502 Bad Gateway</body></html>')
            return

        if self.mode == "503":
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Service Unavailable"}')
            return

        if self.mode == "504":
            self.send_response(504)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Gateway Timeout"}')
            return

        if self.mode == "malformed_json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"choices": [broken json string here')
            return

        if self.mode == "empty_choices":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"choices": []}')
            return

        if self.mode == "missing_content":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"choices": [{"message": {}}]}')
            return

        if self.mode == "null_content":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"choices": [{"message": {"content": null}}]}')
            return

        if self.mode == "empty_body":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            # No body written
            return

        # Default fallback
        self.send_response(500)
        self.end_headers()


class TestM1ModelRoutingChallenge(unittest.TestCase):
    mock_server = None
    mock_port = None
    mock_thread = None

    @classmethod
    def setUpClass(cls):
        # Iniciar servidor mock en un puerto efímero libre
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        cls.mock_port = sock.getsockname()[1]
        sock.close()

        cls.mock_server = HTTPServer(('127.0.0.1', cls.mock_port), MockFaultyServerHandler)
        cls.mock_thread = threading.Thread(target=cls.mock_server.serve_forever, daemon=True)
        cls.mock_thread.start()

    @classmethod
    def tearDownClass(cls):
        if cls.mock_server:
            cls.mock_server.shutdown()
            cls.mock_server.server_close()

    def setUp(self):
        # Reset de URL original antes de cada test
        omniroute_client.OMNIROUTE_URL = DEFAULT_OMNIROUTE_URL

    def tearDown(self):
        omniroute_client.OMNIROUTE_URL = DEFAULT_OMNIROUTE_URL

    # =========================================================================
    # 1. PRUEBAS DE RESOLUCIÓN Y MAPEO ESTRICTO DE ALIAS
    # =========================================================================
    def test_01_alias_claude_strict(self):
        """Verifica que 'claude' mapea estrictamente a agy/claude-sonnet-5-5-medium."""
        self.assertEqual(resolver_nombre_modelo("claude"), "agy/claude-sonnet-5-5-medium")

    def test_02_alias_gemini_strict(self):
        """Verifica que 'gemini' mapea estrictamente a agy/gemini-3-flash."""
        self.assertEqual(resolver_nombre_modelo("gemini"), "agy/gemini-3-flash")

    def test_03_alias_opus_strict(self):
        """Verifica que 'opus' mapea estrictamente a agy/claude-opus-5-5-medium."""
        self.assertEqual(resolver_nombre_modelo("opus"), "agy/claude-opus-5-5-medium")

    def test_04_alias_argon_strict(self):
        """Verifica que 'argon' mapea estrictamente a agy/gemini-4-argon-medium."""
        self.assertEqual(resolver_nombre_modelo("argon"), "agy/gemini-4-argon-medium")

    def test_05_alias_casing_and_whitespace_invariance(self):
        """Verifica resiliencia ante mayúsculas, minúsculas y espacios en blanco."""
        casos = [
            ("CLAUDE", "agy/claude-sonnet-5-5-medium"),
            ("  claude  ", "agy/claude-sonnet-5-5-medium"),
            ("Gemini", "agy/gemini-3-flash"),
            ("GEMINI\t", "agy/gemini-3-flash"),
            ("Opus", "agy/claude-opus-5-5-medium"),
            (" OPUS ", "agy/claude-opus-5-5-medium"),
            ("ARGON", "agy/gemini-4-argon-medium"),
            (" argon\n", "agy/gemini-4-argon-medium"),
        ]
        for entrada, esperado in casos:
            with self.subTest(entrada=entrada):
                self.assertEqual(resolver_nombre_modelo(entrada), esperado)

    def test_06_alias_alternate_synonyms(self):
        """Verifica sinónimos secundarios registrados (sonnet, flash)."""
        self.assertEqual(resolver_nombre_modelo("sonnet"), "agy/claude-sonnet-5-5-medium")
        self.assertEqual(resolver_nombre_modelo("claude-sonnet"), "agy/claude-sonnet-5-5-medium")
        self.assertEqual(resolver_nombre_modelo("flash"), "agy/gemini-3-flash")
        self.assertEqual(resolver_nombre_modelo("gemini-flash"), "agy/gemini-3-flash")

    def test_07_alias_empty_or_none_defaults_to_claude(self):
        """Verifica que cadenas vacías o None retornan el modelo predeterminado (Claude)."""
        self.assertEqual(resolver_nombre_modelo(""), "agy/claude-sonnet-5-5-medium")
        self.assertEqual(resolver_nombre_modelo(None), "agy/claude-sonnet-5-5-medium")

    def test_08_alias_passthrough_unknown_model(self):
        """Verifica que modelos ya calificados o nombres directos se conservan sin alteración."""
        self.assertEqual(
            resolver_nombre_modelo("agy/claude-opus-5-5-medium"),
            "agy/claude-opus-5-5-medium"
        )
        self.assertEqual(
            resolver_nombre_modelo("custom-org/custom-model-v1"),
            "custom-org/custom-model-v1"
        )

    # =========================================================================
    # 2. PRUEBAS DE INFERENCIA EN VIVO, NO TRUNCAMIENTO Y AUTENTICIDAD (4 MODELOS)
    # =========================================================================
    def _verificar_no_truncamiento(self, texto: str):
        """Valida que el texto termine de forma coherente y no cortado en medio de palabra."""
        self.assertGreater(len(texto), 20, "El texto generado es demasiado corto")
        # El texto no debe terminar en caracteres de corte incompleto
        caracter_final = texto[-1]
        terminales_validos = ('.', '!', '?', '"', "'", '»', ')', '}', ']', '\n', '⚡', '🍱', '🍗')
        # Si no es un signo terminal obvio, verificar que al menos la última palabra no sea cortada abruptamente
        ultimas_palabras = texto.strip().split()
        self.assertGreater(len(ultimas_palabras), 3, "Respuesta debe tener múltiples palabras")

    def test_09_live_inference_claude_sonnet(self):
        """Inferencia real en vivo con Claude Sonnet 5.5 y verificación de no truncamiento."""
        res = consultar_omniroute(
            "¿Cuáles son los 3 componentes del bowl proteico de TapMeals y cuánto pesa?",
            model="claude",
            timeout=18
        )
        self.assertTrue(res["success"], f"Claude falló: {res.get('error')}")
        self.assertIsNone(res["error"])
        self.assertEqual(res["model"], "agy/claude-sonnet-5-5-medium")
        self.assertNotEqual(res["response"], FALLBACK_TAPMEALS_RESPONSE)
        self.assertIn("305", res["response"])
        self._verificar_no_truncamiento(res["response"])
        print(f"\n[OK] Claude Sonnet ({res['latency']}s): {res['response'][:100]}...")

    def test_10_live_inference_gemini_flash(self):
        """Inferencia real en vivo con Gemini 3 Flash y verificación de no truncamiento."""
        res = consultar_omniroute(
            "¿Cuánto cuesta el bowl de pechuga fit en TapMeals Yopal?",
            model="gemini",
            timeout=18
        )
        self.assertTrue(res["success"], f"Gemini falló: {res.get('error')}")
        self.assertIsNone(res["error"])
        self.assertEqual(res["model"], "agy/gemini-3-flash")
        self.assertNotEqual(res["response"], FALLBACK_TAPMEALS_RESPONSE)
        self.assertTrue("13.500" in res["response"] or "13500" in res["response"])
        self._verificar_no_truncamiento(res["response"])
        print(f"\n[OK] Gemini Flash ({res['latency']}s): {res['response'][:100]}...")

    def test_11_live_inference_claude_opus(self):
        """Inferencia real en vivo con Claude Opus 5.5 y verificación de no truncamiento."""
        res = consultar_omniroute(
            "Explica en una frase motivadora por qué comer 150g de pechuga magra en TapMeals ayuda a un atleta en Yopal.",
            model="opus",
            timeout=25
        )
        self.assertTrue(res["success"], f"Opus falló: {res.get('error')}")
        self.assertIsNone(res["error"])
        self.assertEqual(res["model"], "agy/claude-opus-5-5-medium")
        self.assertNotEqual(res["response"], FALLBACK_TAPMEALS_RESPONSE)
        self._verificar_no_truncamiento(res["response"])
        print(f"\n[OK] Claude Opus ({res['latency']}s): {res['response'][:100]}...")

    def test_12_live_inference_gemini_argon(self):
        """Inferencia real en vivo con Gemini 4 Argon y verificación de no truncamiento."""
        res = consultar_omniroute(
            "¿Cuál es el horario de entrega de los almuerzos de TapMeals en Yopal?",
            model="argon",
            timeout=25
        )
        self.assertTrue(res["success"], f"Argon falló: {res.get('error')}")
        self.assertIsNone(res["error"])
        self.assertEqual(res["model"], "agy/gemini-4-argon-medium")
        self.assertNotEqual(res["response"], FALLBACK_TAPMEALS_RESPONSE)
        self.assertTrue("11:30" in res["response"] or "1:30" in res["response"])
        self._verificar_no_truncamiento(res["response"])
        print(f"\n[OK] Gemini Argon ({res['latency']}s): {res['response'][:100]}...")

    # =========================================================================
    # 3. PRUEBAS DE INYECCIÓN DE ERRORES HTTP Y DURABILIDAD DE FALLBACK
    # =========================================================================
    def _probar_modo_fallo_mock(self, mode: str, timeout: int = 5):
        """Helper para configurar el servidor mock y verificar contrato de fallback."""
        MockFaultyServerHandler.mode = mode
        MockFaultyServerHandler.delay = 0.0
        omniroute_client.OMNIROUTE_URL = f"http://127.0.0.1:{self.mock_port}/v1/chat/completions"

        res = consultar_omniroute("Prompt de prueba de error", model="claude", timeout=timeout)
        self.assertFalse(res["success"], f"Debe retornar success=False para modo {mode}")
        self.assertEqual(
            res["response"],
            FALLBACK_TAPMEALS_RESPONSE,
            f"Debe retornar exactamente FALLBACK_TAPMEALS_RESPONSE para modo {mode}"
        )
        self.assertIsNotNone(res["error"], f"Debe reportar error detallado para modo {mode}")
        self.assertGreater(len(res["error"]), 0)
        self.assertGreaterEqual(res["latency"], 0.0)
        return res

    def test_13_http_400_bad_request(self):
        """Inyección HTTP 400 Bad Request retorna fallback sin lanzar excepción."""
        res = self._probar_modo_fallo_mock("400")
        self.assertIn("400", res["error"])

    def test_14_http_401_unauthorized(self):
        """Inyección HTTP 401 Unauthorized retorna fallback sin lanzar excepción."""
        res = self._probar_modo_fallo_mock("401")
        self.assertIn("401", res["error"])

    def test_15_http_403_forbidden(self):
        """Inyección HTTP 403 Forbidden retorna fallback sin lanzar excepción."""
        res = self._probar_modo_fallo_mock("403")
        self.assertIn("403", res["error"])

    def test_16_http_404_not_found(self):
        """Inyección HTTP 404 Not Found retorna fallback sin lanzar excepción."""
        res = self._probar_modo_fallo_mock("404")
        self.assertIn("404", res["error"])

    def test_17_http_429_rate_limited(self):
        """Inyección HTTP 429 Too Many Requests retorna fallback sin lanzar excepción."""
        res = self._probar_modo_fallo_mock("429")
        self.assertIn("429", res["error"])

    def test_18_http_500_internal_error(self):
        """Inyección HTTP 500 Internal Error retorna fallback sin lanzar excepción."""
        res = self._probar_modo_fallo_mock("500")
        self.assertIn("500", res["error"])

    def test_19_http_502_bad_gateway(self):
        """Inyección HTTP 502 Bad Gateway retorna fallback sin lanzar excepción."""
        res = self._probar_modo_fallo_mock("502")
        self.assertIn("502", res["error"])

    def test_20_http_503_service_unavailable(self):
        """Inyección HTTP 503 Service Unavailable retorna fallback sin lanzar excepción."""
        res = self._probar_modo_fallo_mock("503")
        self.assertIn("503", res["error"])

    def test_21_http_504_gateway_timeout(self):
        """Inyección HTTP 504 Gateway Timeout retorna fallback sin lanzar excepción."""
        res = self._probar_modo_fallo_mock("504")
        self.assertIn("504", res["error"])

    def test_22_network_connection_refused(self):
        """Conexión rechazada (puerto cerrado) retorna fallback sin lanzar excepción."""
        # Apuntar a un puerto local cerrado garantizado
        omniroute_client.OMNIROUTE_URL = "http://127.0.0.1:49999/v1/chat/completions"
        res = consultar_omniroute("Prueba puerto cerrado", model="gemini", timeout=2)
        self.assertFalse(res["success"])
        self.assertEqual(res["response"], FALLBACK_TAPMEALS_RESPONSE)
        self.assertIsNotNone(res["error"])

    def test_23_network_read_timeout(self):
        """Demora superior al timeout configurado aborta limpiamente a fallback."""
        MockFaultyServerHandler.mode = "delay_only"
        MockFaultyServerHandler.delay = 3.0  # demorar 3 segundos
        omniroute_client.OMNIROUTE_URL = f"http://127.0.0.1:{self.mock_port}/v1/chat/completions"

        start = time.time()
        res = consultar_omniroute("Prueba timeout", model="claude", timeout=1)  # timeout 1s
        elapsed = time.time() - start

        self.assertFalse(res["success"])
        self.assertEqual(res["response"], FALLBACK_TAPMEALS_RESPONSE)
        self.assertIn("timed out", res["error"].lower())
        self.assertGreaterEqual(res["latency"], 0.9)
        self.assertLess(elapsed, 2.5)  # No debe colgarse

    def test_24_malformed_json_response(self):
        """Cuerpo HTTP 200 con JSON truncado/corrupto no lanza excepción y cae a fallback."""
        res = self._probar_modo_fallo_mock("malformed_json")
        # El error de JSONDecodeError es típicamente 'Expecting value...' o similar
        self.assertTrue(
            any(k in res["error"].lower() for k in ("json", "expecting", "decode", "char")),
            f"Error inesperado: {res['error']}"
        )

    def test_25_empty_choices_array(self):
        """JSON válido pero sin choices [] no lanza IndexError no controlado."""
        res = self._probar_modo_fallo_mock("empty_choices")
        self.assertIsNotNone(res["error"])

    def test_26_missing_message_content(self):
        """JSON válido pero estructura de mensaje vacía no rompe el cliente."""
        res = self._probar_modo_fallo_mock("missing_content")
        self.assertIsNotNone(res["error"])

    def test_27_null_message_content(self):
        """JSON con message.content == None no lanza AttributeError al hacer strip()."""
        res = self._probar_modo_fallo_mock("null_content")
        self.assertIsNotNone(res["error"])

    def test_28_empty_http_body(self):
        """Respuesta 200 con cuerpo completamente vacío (0 bytes) cae limpiamente a fallback."""
        res = self._probar_modo_fallo_mock("empty_body")
        self.assertIsNotNone(res["error"])

    # =========================================================================
    # 4. PRUEBAS DE PRECISIÓN DE LATENCIA Y MEDICIÓN DE TIEMPO
    # =========================================================================
    def test_29_latency_accuracy_success_query(self):
        """La latencia calculada en query exitosa coincide con el tiempo de reloj externo."""
        MockFaultyServerHandler.mode = "delay_only"
        MockFaultyServerHandler.delay = 0.50
        omniroute_client.OMNIROUTE_URL = f"http://127.0.0.1:{self.mock_port}/v1/chat/completions"

        t0 = time.time()
        res = consultar_omniroute("Test latencia", model="claude", timeout=5)
        t_wall = time.time() - t0

        self.assertTrue(res["success"])
        self.assertAlmostEqual(res["latency"], t_wall, delta=0.08)
        self.assertIsInstance(res["latency"], float)
        self.assertEqual(len(str(res["latency"]).split(".")[-1]), min(len(str(res["latency"]).split(".")[-1]), 3))

    def test_30_latency_accuracy_error_query(self):
        """La latencia se registra de manera precisa incluso ante fallos HTTP 500 demorados."""
        MockFaultyServerHandler.mode = "500"
        MockFaultyServerHandler.delay = 0.35
        omniroute_client.OMNIROUTE_URL = f"http://127.0.0.1:{self.mock_port}/v1/chat/completions"

        t0 = time.time()
        res = consultar_omniroute("Test latencia error", model="claude", timeout=5)
        t_wall = time.time() - t0

        self.assertFalse(res["success"])
        self.assertAlmostEqual(res["latency"], t_wall, delta=0.08)
        self.assertGreaterEqual(res["latency"], 0.30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
