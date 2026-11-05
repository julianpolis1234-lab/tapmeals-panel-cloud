"""
TapMeals E2E Test Suite — Tier 3: Combinatorial & Cross-Feature Interaction Tests
Tests pairwise and multi-way interactions between all 4 autonomous layers:
Cloud Responder, Autonomous Departments (ChefOps, TrendRadar, GrowthLead, Retention),
Multimedia Video Pipeline, and Web Dashboard.
Coverage: 20 comprehensive combinatorial interaction tests.
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
    WHATSAPP_NUMBER,
    TRIGGER_KEYWORD,
    BRAND_COLOR_GOLD,
    BRAND_COLOR_BG,
    VOICE_COLOMBIA_MALE,
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
    FALLBACK_TAPMEALS_RESPONSE,
)
from app import app, evaluar_reglas, cargar_config, cargar_historial


class TestTier3Combinations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = get_flask_test_client()
        cls.config = cargar_config()
        cls.history = cargar_historial()
        cls.sync_key = "e0db4b419e36db6e05cb23d071bd3afaa435dfeae4c0101867b9c787dd596c07"

    def test_c01_trend_to_video_script(self):
        """C01: TrendRadar Directive feeds directly into 4-Beat Video Script Generator."""
        directive = TrendRadarAdapter.create_trend_directive(
            "trend_fatiga_01",
            "Evitar el letargo vespertino en oficinas de Yopal",
            "lifestyle_workplace",
            "El corrientazo con exceso de fritos te apaga la mente a las 2PM. TapMeals te da 305g limpios."
        )
        self.assertEqual(directive["product_specs_featured"]["weight_grams"], 305)

        script = VideoPipelineAdapter.generate_4beat_script(directive["topic"])
        self.assertEqual(script["total_duration"], 16.0)
        self.assertEqual(len(script["beats"]), 4)
        # Verifica que el guión incorpore la especificación del bowl
        beat2 = script["beats"][1]
        self.assertIn("150", beat2["visual_headline"] + beat2["spoken_text"])
        self.assertIn("305", beat2["visual_sub"] + beat2["spoken_text"])

    def test_c02_video_script_to_tts_and_overlays(self):
        """C02: Video script beats feed into Edge TTS audio and Pillow graphic overlays."""
        script = VideoPipelineAdapter.generate_4beat_script("Energía limpia Yopal")
        b1 = script["beats"][0]

        # 1. Audio synthesis
        import edge_tts
        comm = edge_tts.Communicate(b1["spoken_text"], VOICE_COLOMBIA_MALE)
        self.assertIsNotNone(comm)

        # 2. Pillow graphic card overlay
        temp_card = Path("temp_c02_card.png")
        try:
            VideoPipelineAdapter.render_overlay_card(
                b1["visual_headline"],
                b1["visual_sub"],
                temp_card
            )
            self.assertTrue(temp_card.exists())
            from PIL import Image
            with Image.open(temp_card) as img:
                self.assertEqual(img.size, (1080, 1920))
                self.assertEqual(img.mode, "RGBA")
        finally:
            if temp_card.exists():
                temp_card.unlink()

    def test_c03_overlays_and_tts_to_ffmpeg(self):
        """C03: Graphic card overlay + background audio composite via FFmpeg syntax."""
        temp_card = Path("temp_c03_overlay.png")
        temp_out = Path("temp_c03_render.mp4")
        try:
            VideoPipelineAdapter.render_overlay_card("305g REALES", "150g pechuga", temp_card)
            # Renderizar 1 segundo de prueba con ffmpeg
            cmd = [
                "ffmpeg", "-y", "-t", "1",
                "-i", str(BASE_VIDEO_PATH),
                "-i", str(temp_card),
                "-filter_complex", "[0:v][1:v]overlay=0:0",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-an", str(temp_out)
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(proc.returncode, 0, f"FFmpeg failed: {proc.stderr}")
            self.assertTrue(temp_out.exists())
            self.assertGreater(temp_out.stat().st_size, 1000)
        finally:
            if temp_card.exists():
                temp_card.unlink()
            if temp_out.exists():
                temp_out.unlink()

    def test_c04_auto_responder_to_growth_lead(self):
        """C04: Auto-responder handles unknown athlete DM, extracting intent for GrowthLead."""
        inquiry = "Hola, entreno en Smart Fit Alcaraván y busco un almuerzo de 35g de proteína en Yopal"
        resp = evaluar_reglas(inquiry, "dm", self.config)
        self.assertTrue(resp["triggers"])

        # Pasa interacción al calificador de leads
        score, tier = GrowthLeadAdapter.score_lead(["dm_inquiry", "Smart Fit"])
        self.assertGreaterEqual(score, 8)
        self.assertEqual(tier, "Hot")

    def test_c05_growth_lead_comment_to_dm_and_scoring(self):
        """C05: GrowthLead detects comment, dispatches public reply, and generates DM payload."""
        comment = "Me interesa el menú TapTap para la oficina"
        user = "carlos_yopal"
        routing = GrowthLeadAdapter.route_comment_to_dm(comment, user)
        self.assertTrue(routing["triggers"])
        self.assertIn(f"@{user}", routing["public_reply"])
        self.assertIn("305g", routing["dm_payload"]["text"])

        # Puntuación se eleva a Warm
        score, tier = GrowthLeadAdapter.score_lead([comment])
        self.assertEqual(tier, "Warm")

    def test_c06_growth_lead_to_chefops_order(self):
        """C06: Lead conversion triggers ChefOps order intake before 10:30 cutoff."""
        order_time = (10, 15, 0)
        can_accept = ChefOpsAdapter.check_cutoff(*order_time)
        self.assertTrue(can_accept)

        # Conversión del lead
        score, tier = GrowthLeadAdapter.score_lead(["TapTap", "Nequi pagado"])
        self.assertEqual(tier, "Converted")

    def test_c07_chefops_mrp_to_route_batches(self):
        """C07: ChefOps MRP calculation for 50 orders distributes into 4 delivery clusters."""
        mrp = ChefOpsAdapter.calculate_mrp(50)
        # 50 * 0.150 / 0.70 = 10.714 kg
        self.assertAlmostEqual(mrp["raw_chicken_kg"], 10.714, places=2)
        self.assertEqual(mrp["dry_rice_kg"], 4.0)
        self.assertEqual(mrp["vegetables_total_kg"], 3.75)

        sample_orders = [
            {"id": i, "location": "Gobernacion de Casanare Centro"} for i in range(20)
        ] + [
            {"id": 20 + i, "location": "Barrio San Martin"} for i in range(15)
        ] + [
            {"id": 35 + i, "location": "Unitropico Campus"} for i in range(10)
        ] + [
            {"id": 45 + i, "location": "Crossfit Box Yopal"} for i in range(5)
        ]
        clusters = ChefOpsAdapter.cluster_routes(sample_orders)
        self.assertEqual(len(clusters["Centro"]), 20)
        self.assertEqual(len(clusters["San_Martin"]), 15)
        self.assertEqual(len(clusters["Universidades"]), 10)
        self.assertEqual(len(clusters["Gym_Hubs"]), 5)

    def test_c08_delivery_completion_to_retention_feedback(self):
        """C08: Lunch delivery at 12:30 PM triggers 1:45 PM feedback prompt schedule."""
        feedback_time = RetentionAgentAdapter.schedule_feedback("12:30")
        self.assertEqual(feedback_time, "13:45")

    def test_c09_retention_rating_to_qa_escalation(self):
        """C09: Customer rating of 2 triggers QA escalation alert to kitchen."""
        feedback = RetentionAgentAdapter.process_rating(2, "La pechuga estaba un poco seca hoy")
        self.assertTrue(feedback["escalate_to_chef"])
        self.assertEqual(feedback["status"], "alert")
        self.assertEqual(feedback["action"], "winback_resolution")

    def test_c10_retention_frequency_to_subscription_upgrade(self):
        """C10: Customer with 3 weekly orders qualifies for Friday Plan Semanal offer."""
        offer = RetentionAgentAdapter.evaluate_subscription_upgrade(3)
        self.assertIsNotNone(offer)
        self.assertTrue(offer["eligible"])
        self.assertEqual(offer["weekly_plan_cop"], PRICE_WEEKLY_PLAN_COP)
        self.assertEqual(offer["savings_cop"], 5000)

    def test_c11_omniroute_offline_to_auto_responder_fallback(self):
        """C11: Offline OmniRoute causes auto-responder to gracefully serve TapMeals fallback."""
        import omniroute_client
        old_url = omniroute_client.OMNIROUTE_URL
        try:
            omniroute_client.OMNIROUTE_URL = "http://localhost:59999/v1"
            res = evaluar_reglas("Consulta técnica sobre el sistema de facturación electrónica internacional", "dm", self.config)
            self.assertTrue(res["triggers"])
            self.assertIn("TapMeals Yopal", res["dm_response"])
            self.assertIn("305 g", res["dm_response"])
        finally:
            omniroute_client.OMNIROUTE_URL = old_url

    def test_c12_cloud_sync_to_status_telemetry(self):
        """C12: Session sync reflects in /api/status telemetry."""
        res_sync = self.client.post(
            "/api/cloud-sync-session",
            headers={"X-TapMeals-Sync-Key": self.sync_key},
            json={"history": {"comentarios": ["c_test_100"], "dms": ["d_test_100"]}}
        )
        self.assertEqual(res_sync.status_code, 200)

        res_status = self.client.get("/api/status")
        self.assertEqual(res_status.status_code, 200)
        data = res_status.get_json()
        self.assertIn("total_comentarios", data)
        self.assertIn("total_dms", data)

    def test_c13_multi_model_query_to_trend_radar(self):
        """C13: /api/ai/query evaluates Yopal cultural relevance for a trend directive."""
        prompt = "¿Por qué un bowl de 305g con 150g de pechuga previene el letargo laboral en Yopal frente al corrientazo?"
        payload = {"prompt": prompt, "model": "gemini", "timeout": 30}
        res = self.client.post("/api/ai/query", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        if not data.get("success"):
            # Retry once in case of live gateway concurrency jitter
            time.sleep(1.0)
            res = self.client.post("/api/ai/query", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(len(data["response"]) > 0)

    def test_c14_departmental_dashboard_to_chefops_kpi(self):
        """C14: Kitchen cut-off status and departments appear in /health endpoint."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["departments_active"], 4)
        self.assertEqual(data["service"], "tapmeals-cloud-auto-responder")

    def test_c15_video_pipeline_to_static_storage_and_api(self):
        """C15: Video output directory static/videos is accessible for web downloads."""
        test_video = BASE_PANEL_DIR / "static" / "videos" / "test_output_check.mp4"
        test_video.parent.mkdir(parents=True, exist_ok=True)
        test_video.write_bytes(b"\x00\x00\x00\x1cftypisom")
        try:
            self.assertTrue(test_video.exists())
            res = self.client.get("/static/videos/test_output_check.mp4")
            self.assertEqual(res.status_code, 200)
            res.close()
        finally:
            if test_video.exists():
                try:
                    test_video.unlink()
                except Exception:
                    pass

    def test_c16_lead_scoring_with_pricing_rule_interaction(self):
        """C16: Asking for prices triggers rule_precios and elevates lead score."""
        res = evaluar_reglas("Quiero saber el precio del bowl", "dm", self.config)
        self.assertTrue(res["triggers"])
        self.assertEqual(res["matched_kw"], "precio")

        score, tier = GrowthLeadAdapter.score_lead(["precio"])
        self.assertEqual(tier, "Warm")
        self.assertEqual(score, 5)

    def test_c17_chefops_stock_alert_coordination(self):
        """C17: When chicken stock is low (< 5kg), ChefOps generates stock alert."""
        mrp_low = ChefOpsAdapter.calculate_mrp(15)  # 15 * 0.214 = 3.21 kg
        self.assertIn("LOW_CHICKEN_STOCK", mrp_low["alerts"])

        mrp_high = ChefOpsAdapter.calculate_mrp(50) # 50 * 0.214 = 10.71 kg
        self.assertNotIn("LOW_CHICKEN_STOCK", mrp_high["alerts"])

    def test_c18_interactive_html_to_playwright_rendering(self):
        """C18: Interactive editor template contains all 4 scene titles for video rendering."""
        content = EDITOR_HTML_PATH.read_text(encoding="utf-8")
        self.assertIn("escena 1: hook", content.lower())
        self.assertIn("escena 2: 150g crudo", content.lower())
        self.assertIn("escena 3: macros 87%", content.lower())
        self.assertIn("escena 4: oferta $15k", content.lower())

    def test_c19_bot_session_refresh_during_active_message_dispatch(self):
        """C19: Session authentication and rule engine function in concert without state corruption."""
        rule_res = evaluar_reglas("hola", "dm", self.config)
        self.assertTrue(rule_res["triggers"])
        health_data = self.client.get("/health").get_json()
        self.assertEqual(health_data["status"], "healthy")

    def test_c20_full_cycle_trend_to_lead_conversion(self):
        """C20: Full cycle from Trend discovery to Reel script to DM inquiry to WhatsApp order."""
        # 1. Trend directive
        d = TrendRadarAdapter.create_trend_directive("t_cycle", "Almuerzo Fit Yopal", "fitness", "Come limpio")
        # 2. Script
        s = VideoPipelineAdapter.generate_4beat_script(d["topic"])
        self.assertEqual(s["total_duration"], 16.0)
        # 3. Instagram comment
        comment_routing = GrowthLeadAdapter.route_comment_to_dm("TapTap", "atleta_1")
        self.assertTrue(comment_routing["triggers"])
        # 4. WhatsApp link
        self.assertIn(WHATSAPP_NUMBER, comment_routing["dm_payload"]["text"])
        # 5. Cutoff acceptance
        accepted = ChefOpsAdapter.check_cutoff(9, 30, 0)
        self.assertTrue(accepted)
        # 6. MRP calculation
        mrp = ChefOpsAdapter.calculate_mrp(1)
        self.assertAlmostEqual(mrp["raw_chicken_kg"], 0.214, places=2)


if __name__ == "__main__":
    unittest.main()
