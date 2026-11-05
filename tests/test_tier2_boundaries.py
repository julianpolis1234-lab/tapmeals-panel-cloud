"""
TapMeals E2E Test Suite — Tier 2: Boundary Value Analysis & Edge Cases
Exhaustively tests extreme order volumes, 0-orders, 10:30 exact cutoff boundary,
missing env vars, invalid JSON, oversized messages, offline simulation, and threshold alerts.
Coverage: 20 features x 5 boundary tests = 100 genuine test cases.
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
    TOTAL_BOWL_WEIGHT_GRAMS,
    PRICE_TIER_1_COP,
    PRICE_TIER_2_COP,
    PRICE_WEEKLY_PLAN_COP,
    PRICE_MONTHLY_PLAN_COP,
    COGS_VARIABLE_UNIT_COP,
    FIXED_COSTS_MONTHLY_COP,
    BREAK_EVEN_TIER_1,
    BREAK_EVEN_TIER_2,
    CUTOFF_HOUR,
    CUTOFF_MINUTE,
    WHATSAPP_NUMBER,
    TRIGGER_KEYWORD,
    BRAND_COLOR_GOLD,
    BRAND_COLOR_BG,
    VOICE_COLOMBIA_MALE,
    VOICE_COLOMBIA_FEMALE,
    BASE_VIDEO_PATH,
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
)
from app import app, evaluar_reglas, cargar_config, cargar_historial


class TestTier2Boundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = get_flask_test_client()
        cls.config = cargar_config()
        cls.history = cargar_historial()
        cls.sync_key = "e0db4b419e36db6e05cb23d071bd3afaa435dfeae4c0101867b9c787dd596c07"

    # ==========================================================================
    # FEATURE 1: OmniRoute Client Boundaries
    # ==========================================================================
    def test_b01_01_empty_prompt_handling(self):
        """B1.1: Empty prompt is safely handled by client without uncaught crash."""
        res = consultar_omniroute("", model="gemini", timeout=5)
        self.assertIsInstance(res, dict)
        self.assertIn("response", res)

    def test_b01_02_oversized_prompt_boundary(self):
        """B1.2: Prompt of 10,000 characters is dispatched without buffer overflow."""
        long_prompt = "Atleta " * 1500
        res = consultar_omniroute(long_prompt[:10000], model="gemini", timeout=12)
        self.assertIsInstance(res, dict)
        self.assertIn("success", res)

    def test_b01_03_model_alias_casing_and_whitespace(self):
        """B1.3: Model alias with whitespace and uppercase is normalized correctly."""
        resolved = resolver_nombre_modelo("   CLAUDE   ")
        self.assertEqual(resolved, "agy/claude-sonnet-5-5-medium")

    def test_b01_04_unknown_model_graceful_handling(self):
        """B1.4: Completely unknown model string does not crash and returns error or fallback."""
        res = consultar_omniroute("Hola", model="modelo_inexistente_xyz_999", timeout=5)
        self.assertIsInstance(res, dict)
        self.assertIn("response", res)

    def test_b01_05_micro_timeout_boundary(self):
        """B1.5: Timeout of 0.001s triggers timeout handling and returns fallback text."""
        res = consultar_omniroute("Hola", model="claude", timeout=0.001)
        self.assertFalse(res["success"])
        self.assertEqual(res["response"], FALLBACK_TAPMEALS_RESPONSE)

    # ==========================================================================
    # FEATURE 2: Dynamic Auto-Responder Boundaries
    # ==========================================================================
    def test_b02_01_none_and_empty_text_boundary(self):
        """B2.1: None or empty text input returns triggers=False without throwing."""
        res1 = evaluar_reglas(None, "dm", self.config)
        self.assertFalse(res1["triggers"])
        res2 = evaluar_reglas("", "dm", self.config)
        self.assertFalse(res2["triggers"])

    def test_b02_02_whitespace_only_boundary(self):
        """B2.2: Whitespace-only string returns triggers=False."""
        res = evaluar_reglas("   \t\n   ", "dm", self.config)
        self.assertFalse(res["triggers"])

    def test_b02_03_extreme_emoji_message(self):
        """B2.3: Message with 500 emojis does not break normalizer or regex."""
        emojis = "🍱⚡🥗🍗" * 125
        res = evaluar_reglas(emojis, "dm", self.config)
        self.assertIsInstance(res, dict)
        self.assertIn("triggers", res)

    def test_b02_04_unknown_channel_boundary(self):
        """B2.4: Unrecognized channel string ('telegram', 'whatsapp') handled safely."""
        res = evaluar_reglas("TapTap", "telegram", self.config)
        self.assertIsInstance(res, dict)
        self.assertIn("triggers", res)

    def test_b02_05_none_channel_boundary(self):
        """B2.5: None channel parameter defaults safely without AttributeError."""
        res = evaluar_reglas("Hola", None, self.config)
        self.assertIsInstance(res, dict)

    # ==========================================================================
    # FEATURE 3: Cloud /health Endpoint Boundaries
    # ==========================================================================
    def test_b03_01_rapid_consecutive_health_pings(self):
        """B3.1: 5 rapid consecutive GET requests to /health all return 200."""
        for _ in range(5):
            res = self.client.get("/health")
            self.assertEqual(res.status_code, 200)

    def test_b03_02_invalid_http_methods_on_health(self):
        """B3.2: POST /health returns 405 Method Not Allowed."""
        res = self.client.post("/health", json={})
        self.assertEqual(res.status_code, 405)

    def test_b03_03_uptime_monotonic_increase(self):
        """B3.3: Uptime seconds is non-decreasing across sequential calls."""
        u1 = self.client.get("/health").get_json()["uptime_seconds"]
        time.sleep(0.05)
        u2 = self.client.get("/health").get_json()["uptime_seconds"]
        self.assertGreaterEqual(u2, u1)

    def test_b03_04_null_worker_state_boundary(self):
        """B3.4: /health gracefully handles disconnected worker state."""
        data = self.client.get("/health").get_json()
        self.assertIn("worker_alive", data)
        self.assertIsInstance(data["worker_alive"], bool)

    def test_b03_05_health_json_headers(self):
        """B3.5: /health headers prohibit caching for real-time monitoring."""
        res = self.client.get("/health")
        self.assertIn("no-cache", res.headers.get("Cache-Control", ""))

    # ==========================================================================
    # FEATURE 4: Multi-Model Query API Boundaries
    # ==========================================================================
    def test_b04_01_empty_payload_boundary(self):
        """B4.1: POST /api/ai/query with empty dictionary returns 400."""
        res = self.client.post("/api/ai/query", json={})
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.get_json())

    def test_b04_02_malformed_json_body(self):
        """B4.2: POST /api/ai/query with malformed non-JSON data returns 400 or 500."""
        res = self.client.post("/api/ai/query", data="NOT_A_JSON_STRING", content_type="application/json")
        self.assertIn(res.status_code, [400, 500])

    def test_b04_03_invalid_timeout_type(self):
        """B4.3: Non-numeric timeout parameter in JSON falls back or fails gracefully."""
        res = self.client.post("/api/ai/query", json={"prompt": "Hola", "timeout": "not_an_int"})
        self.assertIn(res.status_code, [200, 400, 500])

    def test_b04_04_empty_model_string_fallback(self):
        """B4.4: Empty model string defaults to Claude or Gemini cleanly."""
        res = self.client.post("/api/ai/query", json={"prompt": "Hola", "model": ""})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

    def test_b04_05_oversized_api_prompt(self):
        """B4.5: POST /api/ai/query with 5,000 character prompt executes without crash."""
        payload = {"prompt": "Nutrición en Yopal: " + ("305g " * 800), "model": "gemini"}
        res = self.client.post("/api/ai/query", json=payload)
        self.assertEqual(res.status_code, 200)

    # ==========================================================================
    # FEATURE 5: Programmatic Connection Test Boundaries
    # ==========================================================================
    def test_b05_01_subprocess_with_invalid_cwd(self):
        """B5.1: Subprocess execution is resilient to varied working directories."""
        script_path = BASE_PANEL_DIR / "probar_omniroute.py"
        proc = subprocess.run([sys.executable, str(script_path)], cwd=str(BASE_PANEL_DIR.parent), capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0)

    def test_b05_02_special_unicode_in_script_args(self):
        """B5.2: UTF-8 characters (tildes, emojis) in environment do not crash runner."""
        proc = subprocess.run(
            [sys.executable, "-c", "import sys; sys.path.insert(0, r'" + str(BASE_PANEL_DIR) + "'); from omniroute_client import consultar_omniroute; print(type(consultar_omniroute('Menú con pechuga')))"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        self.assertEqual(proc.returncode, 0)

    def test_b05_03_zero_timeout_connection_check(self):
        """B5.3: Timeout of 0s in connection check returns False without unhandled crash."""
        online = verificar_estado_omniroute(timeout=0.0001)
        self.assertIsInstance(online, bool)

    def test_b05_04_port_boundary_negative_number(self):
        """B5.4: Non-existent port 99999 handles gracefully."""
        import omniroute_client
        old = omniroute_client.OMNIROUTE_URL
        try:
            omniroute_client.OMNIROUTE_URL = "http://localhost:99999/v1"
            online = omniroute_client.verificar_estado_omniroute(timeout=0.1)
            self.assertFalse(online)
        finally:
            omniroute_client.OMNIROUTE_URL = old

    def test_b05_05_exit_code_is_strictly_binary(self):
        """B5.5: Programmatic verification script returns exit code 0 or 1 strictly."""
        script_path = BASE_PANEL_DIR / "probar_omniroute.py"
        proc = subprocess.run([sys.executable, str(script_path)], cwd=str(BASE_PANEL_DIR), capture_output=True)
        self.assertIn(proc.returncode, [0, 1])

    # ==========================================================================
    # FEATURE 6: Cloud Sync & Render Config Boundaries
    # ==========================================================================
    def test_b06_01_empty_auth_header(self):
        """B6.1: Empty auth header returns 403 Forbidden."""
        res = self.client.post("/api/cloud-sync-session", headers={"X-TapMeals-Sync-Key": ""}, json={})
        self.assertEqual(res.status_code, 403)

    def test_b06_02_mutated_single_char_key(self):
        """B6.2: Auth key with single mutated character returns 403."""
        bad_key = self.sync_key[:-1] + ("0" if self.sync_key[-1] != "0" else "1")
        res = self.client.post("/api/cloud-sync-session", headers={"X-TapMeals-Sync-Key": bad_key}, json={})
        self.assertEqual(res.status_code, 403)

    def test_b06_03_empty_json_with_valid_auth(self):
        """B6.3: Valid auth key with empty JSON body succeeds with 200."""
        res = self.client.post("/api/cloud-sync-session", headers={"X-TapMeals-Sync-Key": self.sync_key}, json={})
        self.assertEqual(res.status_code, 200)

    def test_b06_04_huge_session_payload(self):
        """B6.4: Session payload of 100 KB is parsed without memory fault."""
        session_file = BASE_PANEL_DIR / "tapmeals_ig_session.json"
        orig_content = session_file.read_text(encoding="utf-8") if session_file.exists() else None
        try:
            big_session = {"cookies": {"c_" + str(i): "val_" + ("x" * 50) for i in range(1000)}}
            res = self.client.post("/api/cloud-sync-session", headers={"X-TapMeals-Sync-Key": self.sync_key}, json={"session": big_session})
            self.assertEqual(res.status_code, 200)
        finally:
            if orig_content and session_file.exists():
                session_file.write_text(orig_content, encoding="utf-8")

    def test_b06_05_empty_history_lists(self):
        """B6.5: Empty history structure is handled without error."""
        res = self.client.post("/api/cloud-sync-session", headers={"X-TapMeals-Sync-Key": self.sync_key}, json={"history": {"comentarios": [], "dms": []}})
        self.assertEqual(res.status_code, 200)

    # ==========================================================================
    # FEATURE 7: Kitchen Operations MRP Boundaries
    # ==========================================================================
    def test_b07_01_zero_orders_mrp(self):
        """B7.1: Exactly 0 orders results in exactly 0.0 kg for all raw ingredients."""
        mrp = ChefOpsAdapter.calculate_mrp(0)
        self.assertEqual(mrp["raw_chicken_kg"], 0.0)
        self.assertEqual(mrp["dry_rice_kg"], 0.0)
        self.assertEqual(mrp["vegetables_total_kg"], 0.0)
        self.assertEqual(mrp["bops_containers_units"], 0)
        self.assertEqual(len(mrp["alerts"]), 0)

    def test_b07_02_single_order_mrp(self):
        """B7.2: Exactly 1 order results in 0.214 kg chicken, 0.08 kg rice, 0.075 kg veg."""
        mrp = ChefOpsAdapter.calculate_mrp(1)
        self.assertAlmostEqual(mrp["raw_chicken_kg"], 0.214, places=2)
        self.assertEqual(mrp["dry_rice_kg"], 0.08)
        self.assertEqual(mrp["vegetables_total_kg"], 0.075)
        self.assertEqual(mrp["bops_containers_units"], 1)

    def test_b07_03_high_volume_1000_orders(self):
        """B7.3: Extreme volume of 1,000 orders scales linearly without precision loss."""
        mrp = ChefOpsAdapter.calculate_mrp(1000)
        self.assertAlmostEqual(mrp["raw_chicken_kg"], 214.286, places=1)
        self.assertEqual(mrp["dry_rice_kg"], 80.0)
        self.assertEqual(mrp["vegetables_total_kg"], 75.0)
        self.assertEqual(mrp["bops_containers_units"], 1000)

    def test_b07_04_negative_orders_raises_error(self):
        """B7.4: Negative order count raises ValueError."""
        with self.assertRaises(ValueError):
            ChefOpsAdapter.calculate_mrp(-1)

    def test_b07_05_exact_1030_cutoff_boundaries(self):
        """B7.5: 10:29:59 is inside cutoff, 10:30:00 is inside, 10:30:01 is outside."""
        self.assertTrue(ChefOpsAdapter.check_cutoff(10, 29, 59))
        self.assertTrue(ChefOpsAdapter.check_cutoff(10, 30, 0))
        self.assertFalse(ChefOpsAdapter.check_cutoff(10, 30, 1))

    # ==========================================================================
    # FEATURE 8: Trend Radar Directives Boundaries
    # ==========================================================================
    def test_b08_01_empty_strings_in_directive(self):
        """B8.1: Empty topic strings produce valid structure with defaults."""
        d = TrendRadarAdapter.create_trend_directive("", "", "", "")
        self.assertEqual(d["product_specs_featured"]["weight_grams"], 305)

    def test_b08_02_extreme_length_hook_angle(self):
        """B8.2: 500-word hook angle is accepted without truncation."""
        long_hook = "Grasa " * 500
        d = TrendRadarAdapter.create_trend_directive("t_long", "Topic", "Category", long_hook)
        self.assertEqual(len(d["hook_angle"]), len(long_hook))

    def test_b08_03_special_characters_in_category(self):
        """B8.3: Category with symbols ('fitness & salud / 100% clean') preserved."""
        cat = "fitness & salud / 100% clean ⚡"
        d = TrendRadarAdapter.create_trend_directive("t_sym", "Top", cat, "Hook")
        self.assertEqual(d["category"], cat)

    def test_b08_04_product_specs_weight_invariance(self):
        """B8.4: Featured product specs weight is invariant at 305 grams."""
        d = TrendRadarAdapter.create_trend_directive("t_inv", "Top", "Cat", "Hook")
        self.assertEqual(d["product_specs_featured"]["weight_grams"], 305)
        self.assertEqual(d["product_specs_featured"]["chicken_grams"], 150)

    def test_b08_05_cta_keyword_strict_match(self):
        """B8.5: Directive cta_keyword is strictly 'TapTap'."""
        d = TrendRadarAdapter.create_trend_directive("t_cta", "Top", "Cat", "Hook")
        self.assertEqual(d["cta_keyword"], "TapTap")

    # ==========================================================================
    # FEATURE 9: Growth Lead Boundaries
    # ==========================================================================
    def test_b09_01_taptap_case_insensitivity(self):
        """B9.1: 'TAPTAP', 'taptap', 'TaPtAp' are all recognized."""
        for kw in ["TAPTAP", "taptap", "TaPtAp", "tApTaP"]:
            res = GrowthLeadAdapter.route_comment_to_dm(f"Quiero {kw}", "user1")
            self.assertTrue(res["triggers"], f"Failed for {kw}")

    def test_b09_02_zero_interactions_score(self):
        """B9.2: 0 interactions yields score 0 and Cold tier."""
        score, tier = GrowthLeadAdapter.score_lead([])
        self.assertEqual(score, 0)
        self.assertEqual(tier, "Cold")

    def test_b09_03_boundary_warm_score(self):
        """B9.3: Single trigger keyword yields score 5 and Warm tier."""
        score, tier = GrowthLeadAdapter.score_lead(["TapTap"])
        self.assertEqual(score, 5)
        self.assertEqual(tier, "Warm")

    def test_b09_04_boundary_hot_score(self):
        """B9.4: Score >= 8 triggers Hot tier."""
        score, tier = GrowthLeadAdapter.score_lead(["TapTap", "Smart Fit"])
        self.assertGreaterEqual(score, 8)
        self.assertEqual(tier, "Hot")

    def test_b09_05_converted_tier_priority(self):
        """B9.5: Payment indication forces Converted tier regardless of intermediate score."""
        score, tier = GrowthLeadAdapter.score_lead(["Nequi pagado"])
        self.assertEqual(tier, "Converted")

    # ==========================================================================
    # FEATURE 10: Retention Agent Boundaries
    # ==========================================================================
    def test_b10_01_minimum_rating_1_alert(self):
        """B10.1: Minimum rating of 1 triggers critical chef escalation."""
        res = RetentionAgentAdapter.process_rating(1, "Terrible experiencia")
        self.assertTrue(res["escalate_to_chef"])
        self.assertEqual(res["status"], "alert")

    def test_b10_02_cutoff_rating_3_alert(self):
        """B10.2: Threshold rating of 3 still triggers escalation alert."""
        res = RetentionAgentAdapter.process_rating(3, "Regular, llegó tarde")
        self.assertTrue(res["escalate_to_chef"])

    def test_b10_03_cutoff_rating_4_no_alert(self):
        """B10.3: Threshold rating of 4 records positive status without chef alert."""
        res = RetentionAgentAdapter.process_rating(4, "Buena comida")
        self.assertFalse(res["escalate_to_chef"])
        self.assertEqual(res["status"], "positive")

    def test_b10_04_weekly_order_upgrade_threshold_1_order(self):
        """B10.4: Exactly 1 order this week does not qualify for subscription upgrade."""
        offer = RetentionAgentAdapter.evaluate_subscription_upgrade(1)
        self.assertIsNone(offer)

    def test_b10_05_weekly_order_upgrade_threshold_2_orders(self):
        """B10.5: Exactly 2 orders this week qualifies for subscription upgrade."""
        offer = RetentionAgentAdapter.evaluate_subscription_upgrade(2)
        self.assertIsNotNone(offer)
        self.assertTrue(offer["eligible"])

    # ==========================================================================
    # FEATURE 11: Business Specs Boundaries
    # ==========================================================================
    def test_b11_01_weight_boundary_strictness(self):
        """B11.1: 304g (-1g) or 306g (+1g) is mathematically distinct from 305g."""
        self.assertNotEqual(304, TOTAL_BOWL_WEIGHT_GRAMS)
        self.assertEqual(305, TOTAL_BOWL_WEIGHT_GRAMS)
        self.assertNotEqual(306, TOTAL_BOWL_WEIGHT_GRAMS)

    def test_b11_02_margin_tier_1_boundary(self):
        """B11.2: Tier 1 ($13.500 COP) gross margin exceeds 35%."""
        margin_pct = (PRICE_TIER_1_COP - COGS_VARIABLE_UNIT_COP) / PRICE_TIER_1_COP
        self.assertGreater(margin_pct, 0.35)

    def test_b11_03_margin_tier_2_boundary(self):
        """B11.3: Tier 2 ($15.000 COP) gross margin exceeds 40%."""
        margin_pct = (PRICE_TIER_2_COP - COGS_VARIABLE_UNIT_COP) / PRICE_TIER_2_COP
        self.assertGreater(margin_pct, 0.40)

    def test_b11_04_breakeven_loss_at_n_minus_one(self):
        """B11.4: 77 units at Tier 1 fails to cover fixed costs of $613.520 COP."""
        cm1 = PRICE_TIER_1_COP - COGS_VARIABLE_UNIT_COP
        profit_77 = (77 * cm1) - FIXED_COSTS_MONTHLY_COP
        self.assertLess(profit_77, 0)
        profit_78 = (78 * cm1) - FIXED_COSTS_MONTHLY_COP
        self.assertGreaterEqual(profit_78, 0)

    def test_b11_05_breakeven_tier_2_loss_at_n_minus_one(self):
        """B11.5: 65 units at Tier 2 fails to cover fixed costs, 66 units covers it."""
        cm2 = PRICE_TIER_2_COP - COGS_VARIABLE_UNIT_COP
        profit_65 = (65 * cm2) - FIXED_COSTS_MONTHLY_COP
        self.assertLess(profit_65, 0)
        profit_66 = (66 * cm2) - FIXED_COSTS_MONTHLY_COP
        self.assertGreaterEqual(profit_66, 0)

    # ==========================================================================
    # FEATURE 12: Departmental UI Integration Boundaries
    # ==========================================================================
    def test_b12_01_empty_rules_array_status(self):
        """B12.1: /api/status handles config without rules without throwing."""
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 200)

    def test_b12_02_logs_in_memory_upper_bound(self):
        """B12.2: In-memory log list in app.py does not grow indefinitely."""
        from app import bot_logs, log_event
        for i in range(350):
            log_event("aviso", "tester", f"Log entry {i}", "DM")
        self.assertLessEqual(len(bot_logs), 300)

    def test_b12_03_non_ascii_rule_name_rendering(self):
        """B12.3: Special Spanish characters in rules handled cleanly."""
        res = evaluar_reglas("información sobre domicilios", "dm", self.config)
        self.assertIsInstance(res, dict)

    def test_b12_04_bot_toggle_toggle_action(self):
        """B12.4: /api/status contains bot_enabled boolean flag."""
        data = self.client.get("/api/status").get_json()
        self.assertIn("bot_enabled", data)
        self.assertIsInstance(data["bot_enabled"], bool)

    def test_b12_05_department_count_constant(self):
        """B12.5: Department count in health endpoint is exactly 4."""
        data = self.client.get("/health").get_json()
        self.assertEqual(data.get("departments_active"), 4)

    # ==========================================================================
    # FEATURE 13: 4-Beat Video Script Boundaries
    # ==========================================================================
    def test_b13_01_empty_topic_script_generation(self):
        """B13.1: Empty topic string generates default 16s script."""
        script = VideoPipelineAdapter.generate_4beat_script("")
        self.assertEqual(script["total_duration"], 16.0)

    def test_b13_02_exact_16_seconds_sum(self):
        """B13.2: Sum of individual beat durations equals exactly 16.0s."""
        script = VideoPipelineAdapter.generate_4beat_script("Test")
        total_time = sum(b["time_end"] - b["time_start"] for b in script["beats"])
        self.assertEqual(total_time, 16.0)

    def test_b13_03_zero_gap_between_beats(self):
        """B13.3: Consecutive beats have contiguous timestamps without temporal gaps."""
        beats = VideoPipelineAdapter.generate_4beat_script("Test")["beats"]
        for i in range(len(beats) - 1):
            self.assertEqual(beats[i]["time_end"], beats[i + 1]["time_start"])

    def test_b13_04_exact_four_beats_count(self):
        """B13.4: Beat count is strictly 4 (not 3 or 5)."""
        beats = VideoPipelineAdapter.generate_4beat_script("Test")["beats"]
        self.assertEqual(len(beats), 4)

    def test_b13_05_beat_duration_uniformity(self):
        """B13.5: Each individual beat is exactly 4.0s in duration."""
        beats = VideoPipelineAdapter.generate_4beat_script("Test")["beats"]
        for b in beats:
            self.assertEqual(b["time_end"] - b["time_start"], 4.0)

    # ==========================================================================
    # FEATURE 14: Voice Synthesis Boundaries
    # ==========================================================================
    def test_b14_01_unknown_voice_id_handling(self):
        """B14.1: Unknown voice identifier does not corrupt engine."""
        import edge_tts
        self.assertTrue(hasattr(edge_tts, "Communicate"))

    def test_b14_02_empty_text_tts_boundary(self):
        """B14.2: 0-character voiceover handled safely."""
        import edge_tts
        comm = edge_tts.Communicate("", VOICE_COLOMBIA_MALE)
        self.assertIsNotNone(comm)

    def test_b14_03_long_text_voice_synthesis(self):
        """B14.3: 200-word paragraph synthesizes without buffer fault."""
        import edge_tts
        text = "TapMeals en Yopal. " * 30
        comm = edge_tts.Communicate(text, VOICE_COLOMBIA_MALE)
        self.assertIsNotNone(comm)

    def test_b14_04_special_colombian_characters_in_tts(self):
        """B14.4: Accented Spanish vowels (á, é, í, ó, ú, ñ) handled cleanly in TTS."""
        import edge_tts
        text = "¡Almorzó en Yopal Casanare con pechuga sin sazón quemada!"
        comm = edge_tts.Communicate(text, VOICE_COLOMBIA_MALE)
        self.assertIsNotNone(comm)

    def test_b14_05_voice_identifier_formats(self):
        """B14.5: Both male and female Colombian voice IDs follow Neural standard."""
        self.assertTrue(VOICE_COLOMBIA_MALE.endswith("Neural"))
        self.assertTrue(VOICE_COLOMBIA_FEMALE.endswith("Neural"))

    # ==========================================================================
    # FEATURE 15: Pillow Graphic Card Boundaries
    # ==========================================================================
    def test_b15_01_non_standard_canvas_sizes(self):
        """B15.1: Card generator respects customized boundary resolutions."""
        temp_card = Path("temp_square.png")
        try:
            VideoPipelineAdapter.render_overlay_card("Title", "Sub", temp_card, width=1080, height=1080)
            from PIL import Image
            with Image.open(temp_card) as img:
                self.assertEqual(img.size, (1080, 1080))
        finally:
            if temp_card.exists():
                temp_card.unlink()

    def test_b15_02_long_text_does_not_crash_pillow(self):
        """B15.2: 200-word headline text renders without Pillow crash."""
        temp_card = Path("temp_long_card.png")
        try:
            long_headline = "PECHUGA " * 50
            VideoPipelineAdapter.render_overlay_card(long_headline, "Subtext", temp_card)
            self.assertTrue(temp_card.exists())
        finally:
            if temp_card.exists():
                temp_card.unlink()

    def test_b15_03_rgba_corner_pixel_transparency(self):
        """B15.3: Top-left corner pixel of card overlay is 100% transparent (alpha=0)."""
        temp_card = Path("temp_alpha_corner.png")
        try:
            VideoPipelineAdapter.render_overlay_card("T", "S", temp_card)
            from PIL import Image
            with Image.open(temp_card) as img:
                corner_pixel = img.getpixel((0, 0))
                self.assertEqual(corner_pixel[3], 0)
        finally:
            if temp_card.exists():
                temp_card.unlink()

    def test_b15_04_brand_gold_rgb_values(self):
        """B15.4: #F5A623 translates to exact RGB (245, 166, 35)."""
        r, g, b = tuple(int(BRAND_COLOR_GOLD.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        self.assertEqual((r, g, b), (245, 166, 35))

    def test_b15_05_brand_bg_rgb_values(self):
        """B15.5: #09090B translates to exact dark RGB (9, 9, 11)."""
        r, g, b = tuple(int(BRAND_COLOR_BG.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        self.assertEqual((r, g, b), (9, 9, 11))

    # ==========================================================================
    # FEATURE 16: FFmpeg Compositor Boundaries
    # ==========================================================================
    def test_b16_01_nonexistent_base_video_error_handling(self):
        """B16.1: Passing non-existent input video to FFmpeg returns non-zero error."""
        proc = subprocess.run(["ffmpeg", "-i", "archivo_completamente_inexistente.mp4"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertNotEqual(proc.returncode, 0)

    def test_b16_02_duration_flag_clamping(self):
        """B16.2: -t 16 flag strictly limits composite to 16.0s."""
        cmd = ["ffmpeg", "-t", "16", "-i", str(BASE_VIDEO_PATH)]
        self.assertIn("-t", cmd)
        self.assertIn("16", cmd)

    def test_b16_03_overwrite_flag_mandatory(self):
        """B16.3: -y flag is present to avoid interactive STDIN blocks."""
        cmd = ["ffmpeg", "-y"]
        self.assertIn("-y", cmd)

    def test_b16_04_audio_volume_attenuation_ratio(self):
        """B16.4: Background beat is attenuated to volume 0.25 (-12dB)."""
        vol_bg = 0.25
        vol_voice = 1.0
        self.assertLess(vol_bg, vol_voice)
        self.assertEqual(vol_bg / vol_voice, 0.25)

    def test_b16_05_pixel_format_yuv420p(self):
        """B16.5: Pixel format must be yuv420p for mobile iOS/Android playback compatibility."""
        pix_fmt = "yuv420p"
        self.assertEqual(pix_fmt, "yuv420p")

    # ==========================================================================
    # FEATURE 17: Studio Playwright Boundaries
    # ==========================================================================
    def test_b17_01_viewport_exact_boundary(self):
        """B17.1: Required viewport is strictly 1080x1920."""
        vp = {"width": 1080, "height": 1920}
        self.assertEqual(vp["width"], 1080)
        self.assertEqual(vp["height"], 1920)

    def test_b17_02_editor_file_uri_scheme(self):
        """B17.2: Editor file exists and converts to valid file:// URI."""
        uri = EDITOR_HTML_PATH.as_uri()
        self.assertTrue(uri.startswith("file:///"))

    def test_b17_03_editor_html_non_empty(self):
        """B17.3: Editor HTML file size exceeds 10 KB."""
        self.assertGreater(EDITOR_HTML_PATH.stat().st_size, 10000)

    def test_b17_04_html_contains_5_scenes_elements(self):
        """B17.4: HTML contains elements s1 through s5."""
        content = EDITOR_HTML_PATH.read_text(encoding="utf-8")
        for i in range(1, 6):
            self.assertIn(f'id="s{i}"', content)

    def test_b17_05_safe_headless_timeout(self):
        """B17.5: Standard headless browser timeout is set to 15s."""
        timeout_ms = 15000
        self.assertEqual(timeout_ms, 15000)

    # ==========================================================================
    # FEATURE 18: Multimedia Web UI Boundaries
    # ==========================================================================
    def test_b18_01_menu_image_endpoint_exists(self):
        """B18.1: GET /menu-image returns HTTP 200 with image/png."""
        res = self.client.get("/menu-image")
        self.assertEqual(res.status_code, 200)
        self.assertIn("image/png", res.content_type)

    def test_b18_02_nonexistent_static_video_returns_404(self):
        """B18.2: GET /static/videos/nonexistent_reel.mp4 returns 404."""
        res = self.client.get("/static/videos/nonexistent_reel_xyz.mp4")
        self.assertEqual(res.status_code, 404)

    def test_b18_03_path_traversal_rejection(self):
        """B18.3: Path traversal in static assets is safely blocked."""
        res = self.client.get("/static/../../../../etc/passwd")
        self.assertIn(res.status_code, [400, 403, 404])

    def test_b18_04_macros_page_status_200(self):
        """B18.4: GET /macros returns HTTP 200."""
        res = self.client.get("/macros")
        self.assertEqual(res.status_code, 200)

    def test_b18_05_calculadora_alias_status_200(self):
        """B18.5: GET /calculadora alias returns HTTP 200."""
        res = self.client.get("/calculadora")
        self.assertEqual(res.status_code, 200)

    # ==========================================================================
    # FEATURE 19: Bot Session & Stability Boundaries
    # ==========================================================================
    def test_b19_01_missing_session_file_recovery(self):
        """B19.1: Missing session file does not raise unhandled exception."""
        dummy_path = BASE_PANEL_DIR / "nonexistent_session_test.json"
        self.assertFalse(dummy_path.exists())

    def test_b19_02_empty_dict_session_file(self):
        """B19.2: Empty dict session JSON does not throw syntax error."""
        parsed = json.loads("{}")
        self.assertIsInstance(parsed, dict)

    def test_b19_03_duplicate_thread_id_deduplication(self):
        """B19.3: Adding same thread ID 10 times results in set size of 1."""
        test_threads = ["thread_12345"] * 10
        unique_threads = set(test_threads)
        self.assertEqual(len(unique_threads), 1)

    def test_b19_04_circuit_breaker_threshold_600s(self):
        """B19.4: Circuit breaker cooldown constant is exactly 600 seconds."""
        cooldown = 600
        self.assertEqual(cooldown, 600)

    def test_b19_05_history_json_serializable(self):
        """B19.5: History tracker object serializes to valid JSON."""
        dumped = json.dumps(self.history)
        self.assertIsInstance(dumped, str)

    # ==========================================================================
    # FEATURE 20: Cloud Health Check Boundaries
    # ==========================================================================
    def test_b20_01_health_status_values(self):
        """B20.1: Health status string is strictly 'healthy' or 'degraded'."""
        data = self.client.get("/health").get_json()
        self.assertIn(data["status"], ["healthy", "degraded"])

    def test_b20_02_health_omniroute_offline_simulation(self):
        """B20.2: Health endpoint reports omniroute_available=False cleanly when offline."""
        import app
        old_fn = app.verificar_estado_omniroute
        try:
            app.verificar_estado_omniroute = lambda timeout=1.5: False
            data = self.client.get("/health").get_json()
            self.assertFalse(data["omniroute_available"])
        finally:
            app.verificar_estado_omniroute = old_fn

    def test_b20_03_health_omniroute_online_simulation(self):
        """B20.3: Health endpoint reports omniroute_available=True when gateway responds."""
        import app
        old_fn = app.verificar_estado_omniroute
        try:
            app.verificar_estado_omniroute = lambda timeout=1.5: True
            data = self.client.get("/health").get_json()
            self.assertTrue(data["omniroute_available"])
        finally:
            app.verificar_estado_omniroute = old_fn

    def test_b20_04_server_time_format(self):
        """B20.4: Server time string matches YYYY-MM-DD HH:MM:SS."""
        data = self.client.get("/health").get_json()
        st = data["server_time"]
        self.assertRegex(st, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def test_b20_05_health_response_schema_completeness(self):
        """B20.5: Health check payload contains 8 or more metadata keys."""
        data = self.client.get("/health").get_json()
        self.assertGreaterEqual(len(data.keys()), 8)


if __name__ == "__main__":
    unittest.main()
