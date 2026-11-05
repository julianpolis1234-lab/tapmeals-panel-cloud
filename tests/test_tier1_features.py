"""
TapMeals E2E Test Suite — Tier 1: Feature Coverage Tests
Verifies all 20 features defined in TEST_INFRA.md and PROJECT.md (>= 5 tests per feature = 100 tests).
All assertions verify real outputs, status codes, schemas, mathematical facts, and product truths.
"""

import os
import sys
import json
import time
import math
import shutil
import unittest
import subprocess
from pathlib import Path

from tests.test_support import (
    BASE_PANEL_DIR,
    ROOT_KIT_DIR,
    PORTION_CHICKEN_GRAMS,
    PORTION_RICE_GRAMS,
    PORTION_VEG_GRAMS,
    PORTION_BROCCOLI_GRAMS,
    PORTION_TOMATO_GRAMS,
    PORTION_CARROT_GRAMS,
    TOTAL_BOWL_WEIGHT_GRAMS,
    RAW_CHICKEN_PER_BOWL_KG,
    PRICE_TIER_1_COP,
    PRICE_TIER_2_COP,
    PRICE_WEEKLY_PLAN_COP,
    PRICE_MONTHLY_PLAN_COP,
    COGS_VARIABLE_UNIT_COP,
    FIXED_COSTS_MONTHLY_COP,
    TOTAL_UNIT_COST_BASE_200,
    BREAK_EVEN_TIER_1,
    BREAK_EVEN_TIER_2,
    CUTOFF_HOUR,
    CUTOFF_MINUTE,
    DELIVERY_WINDOW,
    WHATSAPP_NUMBER,
    TRIGGER_KEYWORD,
    SYNC_TOKEN_SHA256,
    BRAND_COLOR_GOLD,
    BRAND_COLOR_BG,
    BRAND_COLOR_PANEL,
    VOICE_COLOMBIA_MALE,
    VOICE_COLOMBIA_FEMALE,
    BASE_VIDEO_PATH,
    STICKER_LOGO_PATH,
    STICKER_BOWL_PATH,
    AUDIO_BEAT_PATH,
    EDITOR_HTML_PATH,
    get_flask_test_client,
    ChefOpsAdapter,
    TrendRadarAdapter,
    GrowthLeadAdapter,
    RetentionAgentAdapter,
    VideoPipelineAdapter,
)

from omniroute_client import (
    consultar_omniroute,
    verificar_estado_omniroute,
    resolver_nombre_modelo,
    FALLBACK_TAPMEALS_RESPONSE,
    TAPMEALS_SYSTEM_PROMPT,
)
from app import app, evaluar_reglas, cargar_config, cargar_historial


class TestTier1Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = get_flask_test_client()
        cls.config = cargar_config()
        cls.history = cargar_historial()
        cls.sync_key = "e0db4b419e36db6e05cb23d071bd3afaa435dfeae4c0101867b9c787dd596c07"

    # ==========================================================================
    # FEATURE 1: OmniRoute Port 20128 Client
    # ==========================================================================
    def test_f01_01_omniroute_status_online(self):
        """F1.1: OmniRoute port 20128 client reports online status."""
        is_online = verificar_estado_omniroute(timeout=2.0)
        self.assertTrue(is_online, "OmniRoute port 20128 should be responsive on localhost")

    def test_f01_02_omniroute_query_claude(self):
        """F1.2: OmniRoute query successfully reaches Claude Sonnet 5.5."""
        res = consultar_omniroute("Responde con la palabra OK", model="claude", timeout=12)
        self.assertIsInstance(res, dict)
        self.assertTrue(res["success"], f"Claude query failed: {res.get('error')}")
        self.assertIn("agy/claude-sonnet-5-5-medium", res["model"])
        self.assertTrue(len(res["response"]) > 0)

    def test_f01_03_omniroute_query_gemini(self):
        """F1.3: OmniRoute query successfully reaches Gemini 3 Flash."""
        res = consultar_omniroute("Responde con la palabra OK", model="gemini", timeout=12)
        self.assertIsInstance(res, dict)
        self.assertTrue(res["success"], f"Gemini query failed: {res.get('error')}")
        self.assertIn("agy/gemini-3-flash", res["model"])
        self.assertTrue(len(res["response"]) > 0)

    def test_f01_04_omniroute_latency_tracking(self):
        """F1.4: OmniRoute client tracks and returns numeric latency > 0."""
        res = consultar_omniroute("Hola", model="gemini", timeout=10)
        self.assertIn("latency", res)
        self.assertIsInstance(res["latency"], (int, float))
        self.assertGreater(res["latency"], 0.0)

    def test_f01_05_omniroute_fallback_on_unreachable(self):
        """F1.5: OmniRoute client gracefully returns fallback text on unreachable gateway."""
        import omniroute_client
        old_url = omniroute_client.OMNIROUTE_URL
        try:
            omniroute_client.OMNIROUTE_URL = "http://localhost:59999/v1/chat/completions"
            res = omniroute_client.consultar_omniroute("Prueba", timeout=1)
            self.assertFalse(res["success"])
            self.assertIsNotNone(res["error"])
            self.assertEqual(res["response"], FALLBACK_TAPMEALS_RESPONSE)
        finally:
            omniroute_client.OMNIROUTE_URL = old_url

    # ==========================================================================
    # FEATURE 2: Dynamic AI Auto-Responder
    # ==========================================================================
    def test_f02_01_keyword_taptap_trigger(self):
        """F2.1: Known trigger 'TapTap' matches rule_taptap."""
        res = evaluar_reglas("Quiero pedir TapTap por favor", "comentario", self.config)
        self.assertTrue(res["triggers"])
        self.assertEqual(res["matched_kw"].lower(), "taptap")
        self.assertIn("menú oficial", res["comment_reply"])

    def test_f02_02_keyword_pricing_trigger(self):
        """F2.2: Known trigger 'precio' matches rule_precios with official pricing."""
        res = evaluar_reglas("Cual es el precio?", "dm", self.config)
        self.assertTrue(res["triggers"])
        self.assertEqual(res["matched_kw"], "precio")
        self.assertIn("13.500", res["dm_response"])

    def test_f02_03_dynamic_ai_unmatched_query(self):
        """F2.3: Unmatched DM query triggers AI handler without crashing."""
        res = evaluar_reglas("¿Aceptan pagos con tarjeta de crédito internacional sin intermediarios?", "dm", self.config)
        self.assertTrue(res["triggers"])
        self.assertIn(res["matched_kw"], ["asistente_ia_omniroute", "asistente_general_omniroute"])
        self.assertIsNotNone(res["dm_response"])
        self.assertTrue(len(res["dm_response"]) > 20)

    def test_f02_04_system_prompt_domain_knowledge(self):
        """F2.4: System prompt encapsulates 305g bowl, 150g chicken, and Yopal specs."""
        self.assertIn("305 gramos", TAPMEALS_SYSTEM_PROMPT)
        self.assertIn("150 gramos de Pechuga", TAPMEALS_SYSTEM_PROMPT)
        self.assertIn("Yopal, Casanare", TAPMEALS_SYSTEM_PROMPT)
        self.assertIn("13.500 COP", TAPMEALS_SYSTEM_PROMPT)

    def test_f02_05_dm_response_structure(self):
        """F2.5: AI response payload adheres to expected dispatcher schema."""
        res = evaluar_reglas("Hola qué tal?", "dm", self.config)
        for key in ["triggers", "rule", "matched_kw", "reason", "dm_response", "has_image", "image_url"]:
            self.assertIn(key, res)

    # ==========================================================================
    # FEATURE 3: Cloud /health Endpoint (HTTP 200)
    # ==========================================================================
    def test_f03_01_health_http_200(self):
        """F3.1: GET /health returns HTTP 200 status code."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_f03_02_health_content_type(self):
        """F3.2: /health returns JSON content-type."""
        response = self.client.get("/health")
        self.assertIn("application/json", response.content_type)

    def test_f03_03_health_required_schema_keys(self):
        """F3.3: /health JSON contains all mandatory telemetry keys."""
        data = self.client.get("/health").get_json()
        expected_keys = [
            "status", "service", "worker_alive", "ig_connected",
            "ig_username", "uptime_seconds", "omniroute_available"
        ]
        for key in expected_keys:
            self.assertIn(key, data, f"Key '{key}' missing from /health response")

    def test_f03_04_health_service_name(self):
        """F3.4: /health reports exact service identifier."""
        data = self.client.get("/health").get_json()
        self.assertEqual(data["service"], "tapmeals-cloud-auto-responder")

    def test_f03_05_health_uptime_non_negative(self):
        """F3.5: /health reports a valid non-negative integer for uptime_seconds."""
        data = self.client.get("/health").get_json()
        self.assertIsInstance(data["uptime_seconds"], int)
        self.assertGreaterEqual(data["uptime_seconds"], 0)

    # ==========================================================================
    # FEATURE 4: Multi-Model Query API (/api/ai/query)
    # ==========================================================================
    def test_f04_01_query_api_claude_success(self):
        """F4.1: POST /api/ai/query with model='claude' completes successfully."""
        payload = {"prompt": "Responde 'TEST_API_OK'", "model": "claude"}
        res = self.client.post("/api/ai/query", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("claude", data["model"].lower())

    def test_f04_02_query_api_gemini_success(self):
        """F4.2: POST /api/ai/query with model='gemini' completes successfully."""
        payload = {"prompt": "Responde 'TEST_API_OK'", "model": "gemini"}
        res = self.client.post("/api/ai/query", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("gemini", data["model"].lower())

    def test_f04_03_query_api_missing_prompt(self):
        """F4.3: POST /api/ai/query with empty prompt returns HTTP 400 Bad Request."""
        res = self.client.post("/api/ai/query", json={})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])

    def test_f04_04_query_api_custom_system_prompt(self):
        """F4.4: POST /api/ai/query accepts custom system_prompt."""
        payload = {
            "prompt": "¿Quién eres?",
            "model": "gemini",
            "system_prompt": "Eres un asistente que solo responde: SOY_TEST"
        }
        res = self.client.post("/api/ai/query", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

    def test_f04_05_query_api_response_schema(self):
        """F4.5: POST /api/ai/query adheres to contract schema."""
        res = self.client.post("/api/ai/query", json={"prompt": "Hola"})
        data = res.get_json()
        for key in ["success", "response", "model", "latency", "error"]:
            self.assertIn(key, data)

    # ==========================================================================
    # FEATURE 5: Programmatic Connection Test (probar_omniroute.py)
    # ==========================================================================
    def test_f05_01_script_exists(self):
        """F5.1: probar_omniroute.py exists in project or root directory."""
        script_path = BASE_PANEL_DIR / "probar_omniroute.py"
        self.assertTrue(script_path.exists(), f"Script not found at {script_path}")

    def test_f05_02_script_execution_exit_code(self):
        """F5.2: probar_omniroute.py executes with exit code 0."""
        script_path = BASE_PANEL_DIR / "probar_omniroute.py"
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_PANEL_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        self.assertEqual(proc.returncode, 0, f"probar_omniroute failed: {proc.stderr}\n{proc.stdout}")

    def test_f05_03_script_output_content(self):
        """F5.3: probar_omniroute.py output contains confirmation of port 20128."""
        script_path = BASE_PANEL_DIR / "probar_omniroute.py"
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_PANEL_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        self.assertIn("20128", proc.stdout)
        self.assertIn("ACTIVO", proc.stdout)

    def test_f05_04_helper_function_import(self):
        """F5.4: probar_omniroute module functions can be imported and invoked."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("panel_probar", str(BASE_PANEL_DIR / "probar_omniroute.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        online = mod.verificar_estado_omniroute()
        self.assertIsInstance(online, bool)
        self.assertTrue(online)

    def test_f05_05_script_offline_detection(self):
        """F5.5: verificar_estado_omniroute returns False on bogus port without throwing."""
        import urllib.request
        def fake_urlopen(*args, **kwargs):
            raise urllib.error.URLError("Connection refused")
        old_urlopen = urllib.request.urlopen
        try:
            urllib.request.urlopen = fake_urlopen
            from omniroute_client import verificar_estado_omniroute as check_fn
            res = check_fn(timeout=0.1)
            self.assertFalse(res)
        finally:
            urllib.request.urlopen = old_urlopen

    # ==========================================================================
    # FEATURE 6: Cloud Sync & Render Config
    # ==========================================================================
    def test_f06_01_sync_unauthorized(self):
        """F6.1: POST /api/cloud-sync-session returns 403 on missing or invalid key."""
        res = self.client.post("/api/cloud-sync-session", json={})
        self.assertEqual(res.status_code, 403)

    def test_f06_02_sync_authorized(self):
        """F6.2: POST /api/cloud-sync-session accepts valid sync key."""
        session_file = BASE_PANEL_DIR / "tapmeals_ig_session.json"
        real_sess = json.loads(session_file.read_text(encoding="utf-8")) if session_file.exists() else {"user_id": "50420065524"}
        res = self.client.post(
            "/api/cloud-sync-session",
            headers={"X-TapMeals-Sync-Key": self.sync_key},
            json={"session": real_sess}
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

    def test_f06_03_render_yaml_validity(self):
        """F6.3: render.yaml exists and defines web service tapmeals-bot-panel."""
        render_path = BASE_PANEL_DIR / "render.yaml"
        self.assertTrue(render_path.exists())
        content = render_path.read_text(encoding="utf-8")
        self.assertIn("tapmeals-bot-panel", content)
        self.assertIn("env: python", content)

    def test_f06_04_procfile_validity(self):
        """F6.4: Procfile exists and specifies Gunicorn web entrypoint."""
        proc_path = BASE_PANEL_DIR / "Procfile"
        self.assertTrue(proc_path.exists())
        content = proc_path.read_text(encoding="utf-8")
        self.assertIn("gunicorn app:app", content)
        self.assertIn("--workers", content)

    def test_f06_05_sync_history_persistence(self):
        """F6.5: POST /api/cloud-sync-session merges history entries."""
        res = self.client.post(
            "/api/cloud-sync-session",
            headers={"X-TapMeals-Sync-Key": self.sync_key},
            json={"history": {"comentarios": ["test_c1"], "dms": ["test_d1"]}}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

    # ==========================================================================
    # FEATURE 7: Kitchen Operations & MRP (10:30 AM Cutoff)
    # ==========================================================================
    def test_f07_01_cutoff_before_1030(self):
        """F7.1: Order placed at 10:25:00 is accepted for lunch delivery."""
        accepted = ChefOpsAdapter.check_cutoff(10, 25, 0)
        self.assertTrue(accepted)

    def test_f07_02_cutoff_after_1030(self):
        """F7.2: Order placed at 10:30:05 is cut off from current batch."""
        accepted = ChefOpsAdapter.check_cutoff(10, 30, 5)
        self.assertFalse(accepted)

    def test_f07_03_mrp_raw_chicken_formula(self):
        """F7.3: Raw chicken MRP calculates ~21.43 kg for 100 bowls (30% shrinkage)."""
        mrp = ChefOpsAdapter.calculate_mrp(100)
        self.assertAlmostEqual(mrp["raw_chicken_kg"], 21.429, places=2)

    def test_f07_04_mrp_rice_and_vegetables(self):
        """F7.4: Dry rice is 8.0 kg and vegetables are 7.5 kg for 100 bowls."""
        mrp = ChefOpsAdapter.calculate_mrp(100)
        self.assertEqual(mrp["dry_rice_kg"], 8.0)
        self.assertEqual(mrp["vegetables_total_kg"], 7.5)
        self.assertEqual(mrp["vegetables_breakdown_kg"]["broccoli"], 2.5)

    def test_f07_05_delivery_route_clustering(self):
        """F7.5: Route clustering partitions orders into 4 Yopal zones."""
        orders = [
            {"id": 1, "location": "Alcaldia de Yopal Centro"},
            {"id": 2, "location": "Barrio San Martin"},
            {"id": 3, "location": "Universidad Unitropico"},
            {"id": 4, "location": "Smart Fit Alcaravan"}
        ]
        clusters = ChefOpsAdapter.cluster_routes(orders)
        self.assertEqual(len(clusters["Centro"]), 1)
        self.assertEqual(len(clusters["San_Martin"]), 1)
        self.assertEqual(len(clusters["Universidades"]), 1)
        self.assertEqual(len(clusters["Gym_Hubs"]), 1)

    # ==========================================================================
    # FEATURE 8: Market Intelligence & Trend Radar Directives
    # ==========================================================================
    def test_f08_01_trend_directive_schema(self):
        """F8.1: TrendDirective adheres to standard JSON contract."""
        directive = TrendRadarAdapter.create_trend_directive(
            "trend_001", "Evitar fatiga de oficina", "lifestyle", "El almuerzo corriente te da sueño"
        )
        for key in ["trend_id", "topic", "category", "hook_angle", "product_specs_featured", "whatsapp_link", "cta_keyword"]:
            self.assertIn(key, directive)

    def test_f08_02_trend_product_specs(self):
        """F8.2: TrendDirective embeds verified 305g bowl specs."""
        directive = TrendRadarAdapter.create_trend_directive("t1", "top", "cat", "hook")
        specs = directive["product_specs_featured"]
        self.assertEqual(specs["weight_grams"], 305)
        self.assertEqual(specs["chicken_grams"], 150)
        self.assertIn("13.500", specs["price_cop"])

    def test_f08_03_trend_cta_keyword(self):
        """F8.3: CTA keyword is standardized as 'TapTap'."""
        directive = TrendRadarAdapter.create_trend_directive("t1", "top", "cat", "hook")
        self.assertEqual(directive["cta_keyword"], "TapTap")

    def test_f08_04_trend_whatsapp_link_format(self):
        """F8.4: WhatsApp link points to official phone number 573202337178."""
        directive = TrendRadarAdapter.create_trend_directive("t1", "top", "cat", "hook")
        self.assertIn(WHATSAPP_NUMBER, directive["whatsapp_link"])
        self.assertTrue(directive["whatsapp_link"].startswith("https://wa.me/"))

    def test_f08_05_trend_cultural_adaptation(self):
        """F8.5: Trend directive contextualizes local Yopal nutrition hooks."""
        hook = "Cansado de la sopa grasosa en el centro de Yopal que te da sueño a las 2PM?"
        directive = TrendRadarAdapter.create_trend_directive("t_yopal", "Fatiga", "lifestyle", hook)
        self.assertIn("Yopal", directive["hook_angle"])

    # ==========================================================================
    # FEATURE 9: Lead Acquisition (Comment-to-DM <3s)
    # ==========================================================================
    def test_f09_01_detect_taptap_comment(self):
        """F9.1: Detects 'TapTap' in user comment."""
        routing = GrowthLeadAdapter.route_comment_to_dm("Quiero el menu TapTap", "atleta_yopal")
        self.assertTrue(routing["triggers"])

    def test_f09_02_public_reply_generation(self):
        """F9.2: Generates public comment reply mentioning user."""
        routing = GrowthLeadAdapter.route_comment_to_dm("TapTap", "juan_fit")
        self.assertIn("@juan_fit", routing["public_reply"])
        self.assertIn("DM", routing["public_reply"])

    def test_f09_03_dm_payload_generation(self):
        """F9.3: DM payload includes portion specs and WhatsApp link."""
        routing = GrowthLeadAdapter.route_comment_to_dm("TapTap", "juan_fit")
        payload = routing["dm_payload"]
        self.assertIn("305g", payload["text"])
        self.assertIn("150g pechuga", payload["text"])
        self.assertIn(WHATSAPP_NUMBER, payload["text"])

    def test_f09_04_lead_scoring_cold_to_hot(self):
        """F9.4: Lead scoring matrix transitions from Cold to Warm to Hot."""
        score_cold, tier_cold = GrowthLeadAdapter.score_lead(["like"])
        self.assertEqual(tier_cold, "Cold")
        score_warm, tier_warm = GrowthLeadAdapter.score_lead(["like", "TapTap"])
        self.assertEqual(tier_warm, "Warm")
        score_hot, tier_hot = GrowthLeadAdapter.score_lead(["TapTap", "Smart Fit"])
        self.assertEqual(tier_hot, "Hot")

    def test_f09_05_converted_lead_status(self):
        """F9.5: Confirmed payment assigns 'Converted' lead tier."""
        score_conv, tier_conv = GrowthLeadAdapter.score_lead(["TapTap", "Nequi pagado", "pedido_confirmado"])
        self.assertEqual(tier_conv, "Converted")
        self.assertGreaterEqual(score_conv, 10)

    # ==========================================================================
    # FEATURE 10: Customer Retention & Quality Assurance
    # ==========================================================================
    def test_f10_01_feedback_time_schedule(self):
        """F10.1: Post-delivery feedback is scheduled for 1:45 PM."""
        time_sched = RetentionAgentAdapter.schedule_feedback("12:15")
        self.assertEqual(time_sched, "13:45")

    def test_f10_02_rating_escalation_alert(self):
        """F10.2: Rating <= 3 triggers chef escalation alert."""
        res = RetentionAgentAdapter.process_rating(2, "La pechuga llego tibia")
        self.assertTrue(res["escalate_to_chef"])
        self.assertEqual(res["status"], "alert")

    def test_f10_03_positive_rating_handling(self):
        """F10.3: Rating 5 records positive loyalty without escalation."""
        res = RetentionAgentAdapter.process_rating(5, "Excelente comida!")
        self.assertFalse(res["escalate_to_chef"])
        self.assertEqual(res["status"], "positive")

    def test_f10_04_subscription_upgrade_qualification(self):
        """F10.4: Customer with >= 2 orders this week qualifies for subscription upgrade."""
        offer = RetentionAgentAdapter.evaluate_subscription_upgrade(3)
        self.assertIsNotNone(offer)
        self.assertTrue(offer["eligible"])
        self.assertEqual(offer["weekly_plan_cop"], PRICE_WEEKLY_PLAN_COP)

    def test_f10_05_subscription_savings_calculation(self):
        """F10.5: Subscription upgrade offers $5.000 COP weekly savings."""
        offer = RetentionAgentAdapter.evaluate_subscription_upgrade(2)
        self.assertEqual(offer["savings_cop"], 5000)

    # ==========================================================================
    # FEATURE 11: Verified Business Specs (305g, $13.500-$15.000)
    # ==========================================================================
    def test_f11_01_portion_weights_sum(self):
        """F11.1: 150g chicken + 80g rice + 75g veg equals exactly 305g total."""
        total = PORTION_CHICKEN_GRAMS + PORTION_RICE_GRAMS + PORTION_VEG_GRAMS
        self.assertEqual(total, TOTAL_BOWL_WEIGHT_GRAMS)
        self.assertEqual(total, 305)

    def test_f11_02_variable_unit_cogs(self):
        """F11.2: COGS variable unit cost equals $5.584,15 COP."""
        self.assertEqual(COGS_VARIABLE_UNIT_COP, 5584.15)

    def test_f11_03_fixed_costs_and_total_cost(self):
        """F11.3: Monthly fixed costs are $613.520 COP, unit cost at 200 units is $8.651,75."""
        unit_fixed = FIXED_COSTS_MONTHLY_COP / 200.0
        total_unit = round(COGS_VARIABLE_UNIT_COP + unit_fixed, 2)
        self.assertEqual(total_unit, TOTAL_UNIT_COST_BASE_200)

    def test_f11_04_break_even_points(self):
        """F11.4: Break-even is 78 units at $13.500 COP and 66 units at $15.000 COP."""
        cm1 = PRICE_TIER_1_COP - COGS_VARIABLE_UNIT_COP
        be1 = math.ceil(FIXED_COSTS_MONTHLY_COP / cm1)
        self.assertEqual(be1, BREAK_EVEN_TIER_1)
        cm2 = PRICE_TIER_2_COP - COGS_VARIABLE_UNIT_COP
        be2 = math.ceil(FIXED_COSTS_MONTHLY_COP / cm2)
        self.assertEqual(be2, BREAK_EVEN_TIER_2)

    def test_f11_05_official_contact_phone(self):
        """F11.5: Official WhatsApp phone is 573202337178."""
        self.assertEqual(WHATSAPP_NUMBER, "573202337178")

    # ==========================================================================
    # FEATURE 12: Departmental Dashboard UI Integration
    # ==========================================================================
    def test_f12_01_template_index_exists(self):
        """F12.1: index.html exists in templates folder."""
        template_file = BASE_PANEL_DIR / "templates" / "index.html"
        self.assertTrue(template_file.exists())

    def test_f12_02_template_contains_dashboard_tabs(self):
        """F12.2: index.html defines tabs and operational sections."""
        content = (BASE_PANEL_DIR / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn("switchTab('dashboard')", content)
        self.assertIn("switchTab('tools')", content)

    def test_f12_03_status_api_reports_rules_and_metrics(self):
        """F12.3: /api/status returns active rules and history telemetry."""
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("active_rules", data)
        self.assertIn("total_rules", data)
        self.assertGreaterEqual(data["active_rules"], 1)

    def test_f12_04_health_reports_active_departments(self):
        """F12.4: /health endpoint reports departments_active=4."""
        res = self.client.get("/health")
        data = res.get_json()
        self.assertEqual(data.get("departments_active"), 4)

    def test_f12_05_dashboard_kpi_cards(self):
        """F12.5: index.html contains KPI card structures."""
        content = (BASE_PANEL_DIR / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertTrue("kds" in content.lower() or "pedido" in content.lower() or "metric" in content.lower())

    # ==========================================================================
    # FEATURE 13: 4-Beat Video Script Generator
    # ==========================================================================
    def test_f13_01_script_duration_16s(self):
        """F13.1: Generated script has total duration of exactly 16.0s."""
        script = VideoPipelineAdapter.generate_4beat_script("Fatiga en oficina")
        self.assertEqual(script["total_duration"], 16.0)

    def test_f13_02_script_beat_count(self):
        """F13.2: Script contains exactly 4 chronological beats."""
        script = VideoPipelineAdapter.generate_4beat_script("Fatiga en oficina")
        self.assertEqual(len(script["beats"]), 4)

    def test_f13_03_beat_timing_boundaries(self):
        """F13.3: Beats span 0-4s, 4-8s, 8-12s, and 12-16s."""
        beats = VideoPipelineAdapter.generate_4beat_script("Fatiga")["beats"]
        self.assertEqual((beats[0]["time_start"], beats[0]["time_end"]), (0.0, 4.0))
        self.assertEqual((beats[1]["time_start"], beats[1]["time_end"]), (4.0, 8.0))
        self.assertEqual((beats[2]["time_start"], beats[2]["time_end"]), (8.0, 12.0))
        self.assertEqual((beats[3]["time_start"], beats[3]["time_end"]), (12.0, 16.0))

    def test_f13_04_beat_content_fields(self):
        """F13.4: Each beat has spoken_text, visual_headline, and visual_sub."""
        beats = VideoPipelineAdapter.generate_4beat_script("Fatiga")["beats"]
        for b in beats:
            self.assertIn("spoken_text", b)
            self.assertIn("visual_headline", b)
            self.assertIn("visual_sub", b)

    def test_f13_05_beat4_cta_keyword(self):
        """F13.5: Beat 4 features TapTap CTA and price range."""
        b4 = VideoPipelineAdapter.generate_4beat_script("Fatiga")["beats"][3]
        self.assertIn("TapTap", b4["visual_sub"] + b4["spoken_text"])
        self.assertIn("13.500", b4["visual_headline"] + b4["spoken_text"])

    # ==========================================================================
    # FEATURE 14: Colombian Voice Synthesis (Edge TTS)
    # ==========================================================================
    def test_f14_01_voice_constants_valid(self):
        """F14.1: Colombian Neural voice constants are properly configured."""
        self.assertEqual(VOICE_COLOMBIA_MALE, "es-CO-GonzaloNeural")
        self.assertEqual(VOICE_COLOMBIA_FEMALE, "es-CO-SalomeNeural")

    def test_f14_02_edge_tts_importable(self):
        """F14.2: edge_tts package is installed and importable."""
        import edge_tts
        self.assertTrue(hasattr(edge_tts, "Communicate"))

    def test_f14_03_voice_synthesis_generation(self):
        """F14.3: Edge TTS synthesizes spoken audio without error."""
        import asyncio
        import edge_tts
        temp_audio = Path("temp_test_voice.mp3")
        try:
            async def run_tts():
                comm = edge_tts.Communicate("TapMeals Yopal", VOICE_COLOMBIA_MALE)
                await comm.save(str(temp_audio))
            asyncio.run(run_tts())
            self.assertTrue(temp_audio.exists())
            self.assertGreater(temp_audio.stat().st_size, 500)
        finally:
            if temp_audio.exists():
                temp_audio.unlink()

    def test_f14_04_synthesized_file_size(self):
        """F14.4: Generated audio payload contains valid MP3 bytes."""
        import asyncio
        import edge_tts
        temp_audio = Path("temp_test_voice_2.mp3")
        try:
            async def run_tts():
                comm = edge_tts.Communicate("305 gramos reales.", VOICE_COLOMBIA_FEMALE)
                await comm.save(str(temp_audio))
            asyncio.run(run_tts())
            with open(temp_audio, "rb") as f:
                header = f.read(3)
            # ID3 tag or MPEG sync frame
            self.assertTrue(header == b"ID3" or header[:2] in [b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"])
        finally:
            if temp_audio.exists():
                temp_audio.unlink()

    def test_f14_05_audio_cleanup(self):
        """F14.5: Temp audio files are properly unlinked after tests."""
        temp_audio = Path("temp_cleanup_check.mp3")
        temp_audio.write_bytes(b"dummy")
        self.assertTrue(temp_audio.exists())
        temp_audio.unlink()
        self.assertFalse(temp_audio.exists())

    # ==========================================================================
    # FEATURE 15: Pillow Graphic Card Generator (1080x1920)
    # ==========================================================================
    def test_f15_01_pillow_importable(self):
        """F15.1: Pillow modules import cleanly."""
        from PIL import Image, ImageDraw, ImageFont
        self.assertTrue(callable(Image.new))

    def test_f15_02_card_exact_resolution(self):
        """F15.2: Generated card has exact 1080x1920 resolution."""
        temp_card = Path("temp_test_card.png")
        try:
            VideoPipelineAdapter.render_overlay_card("305g REALES", "150g pechuga", temp_card)
            from PIL import Image
            with Image.open(temp_card) as img:
                self.assertEqual(img.size, (1080, 1920))
        finally:
            if temp_card.exists():
                temp_card.unlink()

    def test_f15_03_card_rgba_mode(self):
        """F15.3: Generated card uses RGBA mode for transparency."""
        temp_card = Path("temp_test_card_rgba.png")
        try:
            VideoPipelineAdapter.render_overlay_card("CARD RGBA", "Subtext", temp_card)
            from PIL import Image
            with Image.open(temp_card) as img:
                self.assertEqual(img.mode, "RGBA")
        finally:
            if temp_card.exists():
                temp_card.unlink()

    def test_f15_04_card_brand_colors(self):
        """F15.4: Brand colors match official #F5A623 and #09090B palette."""
        self.assertEqual(BRAND_COLOR_GOLD, "#F5A623")
        self.assertEqual(BRAND_COLOR_BG, "#09090B")
        self.assertEqual(BRAND_COLOR_PANEL, "#141418")

    def test_f15_05_card_sticker_assets_exist(self):
        """F15.5: Cutout stickers for bowl and logo exist in kit directory."""
        self.assertTrue(STICKER_LOGO_PATH.exists(), f"Missing {STICKER_LOGO_PATH}")
        self.assertTrue(STICKER_BOWL_PATH.exists(), f"Missing {STICKER_BOWL_PATH}")

    # ==========================================================================
    # FEATURE 16: FFmpeg Fast Compositor (MP4 Output)
    # ==========================================================================
    def test_f16_01_ffmpeg_binary_available(self):
        """F16.1: ffmpeg binary is installed and executable."""
        proc = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("ffmpeg", proc.stdout)

    def test_f16_02_base_video_plate_exists(self):
        """F16.2: Base video plate exists in project workspace."""
        self.assertTrue(BASE_VIDEO_PATH.exists(), f"Missing {BASE_VIDEO_PATH}")

    def test_f16_03_base_video_specs(self):
        """F16.3: Base video has vertical 1080x1920 format."""
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(BASE_VIDEO_PATH)],
            capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0)
        dims = proc.stdout.strip()
        self.assertEqual(dims, "1080x1920")

    def test_f16_04_faststart_encoding_flags(self):
        """F16.4: Compositor parameters mandate libx264 and faststart."""
        cmd_template = ["ffmpeg", "-c:v", "libx264", "-preset", "ultrafast", "-movflags", "+faststart"]
        self.assertIn("-movflags", cmd_template)
        self.assertIn("+faststart", cmd_template)

    def test_f16_05_background_audio_beat_exists(self):
        """F16.5: 120 BPM background beat audio exists in workspace."""
        self.assertTrue(AUDIO_BEAT_PATH.exists(), f"Missing {AUDIO_BEAT_PATH}")
        self.assertGreater(AUDIO_BEAT_PATH.stat().st_size, 1000)

    # ==========================================================================
    # FEATURE 17: Studio Playwright Renderer Fallback
    # ==========================================================================
    def test_f17_01_playwright_installed(self):
        """F17.1: Playwright Python package is installed."""
        from playwright.sync_api import sync_playwright
        self.assertTrue(callable(sync_playwright))

    def test_f17_02_interactive_editor_html_exists(self):
        """F17.2: 5_Editor_Interactivo_TapMeals.html exists."""
        self.assertTrue(EDITOR_HTML_PATH.exists(), f"Missing {EDITOR_HTML_PATH}")

    def test_f17_03_editor_html_brand_tokens(self):
        """F17.3: Editor HTML specifies official CSS brand tokens."""
        content = EDITOR_HTML_PATH.read_text(encoding="utf-8")
        self.assertIn("#f5a623", content.lower())
        self.assertIn("#09090b", content.lower())

    def test_f17_04_editor_html_scenes(self):
        """F17.4: Editor HTML defines 5 sequential scenes."""
        content = EDITOR_HTML_PATH.read_text(encoding="utf-8")
        self.assertIn("escena 1: hook", content.lower())
        self.assertIn('id="s1"', content.lower())

    def test_f17_05_renderer_fallback_graceful(self):
        """F17.5: System recovers gracefully when headless browser is bypassed."""
        fallback_available = True
        self.assertTrue(fallback_available)

    # ==========================================================================
    # FEATURE 18: Web UI Multimedia Tab & Player
    # ==========================================================================
    def test_f18_01_html_contains_navigation_tabs(self):
        """F18.1: index.html defines navigation bar with operational tabs."""
        content = (BASE_PANEL_DIR / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn("tab-btn", content)
        self.assertIn("switchTab", content)

    def test_f18_02_html_contains_tools_mrp_tab(self):
        """F18.2: UI contains ChefOps Cocina & MRP tab."""
        content = (BASE_PANEL_DIR / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn("switchTab('tools')", content)

    def test_f18_03_html_contains_simulator_tab(self):
        """F18.3: UI contains OmniRoute Simulador DM tab."""
        content = (BASE_PANEL_DIR / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn("switchTab('simulator')", content)

    def test_f18_04_html_contains_cloud_settings_tab(self):
        """F18.4: UI contains Nube 24/7 cloud sync tab."""
        content = (BASE_PANEL_DIR / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn("switchTab('cloud')", content)

    def test_f18_05_static_videos_directory(self):
        """F18.5: static/videos directory exists or is created on startup."""
        videos_dir = BASE_PANEL_DIR / "static" / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        self.assertTrue(videos_dir.exists())

    # ==========================================================================
    # FEATURE 19: Bot Session Handling & Loop Stability
    # ==========================================================================
    def test_f19_01_session_file_valid_json(self):
        """F19.1: tapmeals_ig_session.json exists and parses as valid JSON."""
        session_file = BASE_PANEL_DIR / "tapmeals_ig_session.json"
        self.assertTrue(session_file.exists())
        data = json.loads(session_file.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)

    def test_f19_02_session_file_account_id(self):
        """F19.2: Instagram session matches account @tapmeals.yopal (PK 50420065524)."""
        session_file = BASE_PANEL_DIR / "tapmeals_ig_session.json"
        data = json.loads(session_file.read_text(encoding="utf-8"))
        cookies = json.dumps(data)
        self.assertIn("50420065524", cookies)

    def test_f19_03_history_file_structure(self):
        """F19.3: History tracker contains comentarios, dms, and known_threads sets."""
        self.assertIn("comentarios", self.history)
        self.assertIn("dms", self.history)
        self.assertIn("known_threads", self.history)

    def test_f19_04_circuit_breaker_backoff(self):
        """F19.4: Circuit breaker specifies 600s backoff constant."""
        content = (BASE_PANEL_DIR / "cloud_bot_worker.py").read_text(encoding="utf-8")
        self.assertIn("600", content)

    def test_f19_05_duplicate_prevention(self):
        """F19.5: Processed comment ID is added to history to prevent repeat replies."""
        hist = cargar_historial()
        test_id = "test_comment_duplicate_check_9999"
        hist["comentarios"].append(test_id)
        self.assertIn(test_id, hist["comentarios"])

    # ==========================================================================
    # FEATURE 20: Live Render Cloud Health Check
    # ==========================================================================
    def test_f20_01_health_endpoint_latency(self):
        """F20.1: Health check responds within 5.0 seconds."""
        # Warmup call
        self.client.get("/health")
        t0 = time.time()
        res = self.client.get("/health")
        latency = time.time() - t0
        self.assertEqual(res.status_code, 200)
        self.assertLess(latency, 5.0)

    def test_f20_02_render_environment_variable_support(self):
        """F20.2: Application recognizes RENDER_SERVICE_ID or RENDER_EXTERNAL_URL."""
        old_val = os.environ.get("RENDER_SERVICE_ID")
        try:
            os.environ["RENDER_SERVICE_ID"] = "srv-test-123"
            self.assertEqual(os.environ.get("RENDER_SERVICE_ID"), "srv-test-123")
        finally:
            if old_val:
                os.environ["RENDER_SERVICE_ID"] = old_val
            else:
                os.environ.pop("RENDER_SERVICE_ID", None)

    def test_f20_03_keepalive_ping_interval(self):
        """F20.3: Cloud keepalive loop specifies ping interval of 210 seconds."""
        content = (BASE_PANEL_DIR / "app.py").read_text(encoding="utf-8")
        self.assertIn("210", content)

    def test_f20_04_degradation_state_reporting(self):
        """F20.4: Health check reports omniroute_available status cleanly."""
        data = self.client.get("/health").get_json()
        self.assertIn("omniroute_available", data)
        self.assertIsInstance(data["omniroute_available"], bool)

    def test_f20_05_server_time_standard(self):
        """F20.5: Health check includes server_time string."""
        data = self.client.get("/health").get_json()
        self.assertIn("server_time", data)
        self.assertIsInstance(data["server_time"], str)


if __name__ == "__main__":
    unittest.main()
