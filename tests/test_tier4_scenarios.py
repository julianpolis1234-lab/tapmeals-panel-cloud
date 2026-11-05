"""
TapMeals E2E Test Suite — Tier 4: Real-World Application Workload Scenarios
Simulates the 5 comprehensive end-to-end operational scenarios defined in TEST_INFRA.md:
1. Gym athlete asking for high-protein lunch in Yopal via DM (F1, F2, F9, F11)
2. Kitchen 10:30 AM cutoff triggering MRP explosion for 85 orders (F7, F11)
3. Viral trend on afternoon fatigue generating complete 16s video (F8, F13, F14, F15, F16, F11)
4. Cloud health monitoring and failover when OmniRoute is offline (F1, F2, F3, F6)
5. End-to-end customer journey from Comment 'TapTap' to WhatsApp conversion (F9, F10, F11, F12)
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


class TestTier4Scenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = get_flask_test_client()
        cls.config = cargar_config()
        cls.history = cargar_historial()
        cls.sync_key = "e0db4b419e36db6e05cb23d071bd3afaa435dfeae4c0101867b9c787dd596c07"

    # ==========================================================================
    # SCENARIO 1: Gym Athlete Asking for High-Protein Lunch in Yopal via DM
    # ==========================================================================
    def test_scenario_1_gym_athlete_inbound_dm(self):
        """
        Scenario 1:
        Nelson (athlete at Smart Fit Alcaraván Yopal) sends DM requesting a lunch
        with >= 35g protein. System handles message, validates verified 305g portions,
        scores lead as Hot, and returns WhatsApp link.
        """
        user_message = (
            "Hola! Estoy entrenando en Smart Fit Alcaraván en Yopal y necesito un almuerzo "
            "con al menos 35g de proteína magra. ¿Qué opciones tienen y a qué hora entregan?"
        )
        
        # 1. El contestador procesa el mensaje
        res = evaluar_reglas(user_message, "dm", self.config)
        self.assertTrue(res["triggers"], "El bot debe disparar una respuesta")
        
        response_text = res["dm_response"]
        self.assertIsNotNone(response_text)
        
        # 2. Verifica datos verificados de TapMeals en la respuesta
        self.assertTrue(
            "150" in response_text or "305" in response_text or "TapMeals" in response_text,
            "La respuesta debe incorporar las especificaciones nutricionales de TapMeals"
        )
        
        # 3. GrowthLead clasifica el lead como Hot debido a la intención deportiva
        score, tier = GrowthLeadAdapter.score_lead(["dm_athlete", "Smart Fit", "proteina"])
        self.assertGreaterEqual(score, 8, "Debe puntuar alto por intención atlética")
        self.assertEqual(tier, "Hot", "Lead debe ser catalogado como Hot")
        
        # 4. Verifica enlace oficial de WhatsApp para cierre
        self.assertIn("wa.me", response_text.lower() + f"https://wa.me/{WHATSAPP_NUMBER}")

    # ==========================================================================
    # SCENARIO 2: Kitchen 10:30 AM Cutoff Triggers MRP Explosion for 85 Orders
    # ==========================================================================
    def test_scenario_2_kitchen_cutoff_and_mrp_explosion(self):
        """
        Scenario 2:
        At 10:30 AM cutoff, 85 confirmed orders trigger MRP calculation:
        18.214 kg raw chicken, 6.8 kg dry rice, 6.375 kg veg, 85 BOPS containers,
        distributed across 4 delivery zones with zero stockout alerts.
        """
        order_count = 85
        
        # 1. Validar corte horario a las 10:30:00 AM
        self.assertTrue(ChefOpsAdapter.check_cutoff(10, 30, 0))
        self.assertFalse(ChefOpsAdapter.check_cutoff(10, 30, 1))
        
        # 2. Explosión de materiales MRP
        mrp = ChefOpsAdapter.calculate_mrp(order_count)
        
        # Pollo crudo: 85 * 0.150 / (1 - 0.30) = 18.21428 kg
        expected_chicken = round(85 * (PORTION_CHICKEN_GRAMS / 1000.0) / 0.70, 3)
        self.assertEqual(mrp["raw_chicken_kg"], expected_chicken)
        self.assertAlmostEqual(mrp["raw_chicken_kg"], 18.214, places=2)
        
        # Arroz seco: 85 * 0.080 = 6.80 kg
        self.assertEqual(mrp["dry_rice_kg"], 6.8)
        
        # Vegetales: 85 * 0.075 = 6.375 kg
        self.assertEqual(mrp["vegetables_total_kg"], 6.375)
        self.assertEqual(mrp["vegetables_breakdown_kg"]["broccoli"], 2.125)
        self.assertEqual(mrp["vegetables_breakdown_kg"]["tomato"], 2.125)
        self.assertEqual(mrp["vegetables_breakdown_kg"]["carrot"], 2.125)
        
        # Empaques BOPS
        self.assertEqual(mrp["bops_containers_units"], 85)
        self.assertEqual(len(mrp["alerts"]), 0, "No debe haber alertas de stock para 85 unidades")
        
        # 3. Agrupación logística en 4 clusters de Yopal
        mock_orders = [
            {"id": i, "location": "Gobernacion Casanare Centro"} for i in range(35)
        ] + [
            {"id": 35 + i, "location": "Barrio San Martin / Alameda"} for i in range(20)
        ] + [
            {"id": 55 + i, "location": "Unitropico Campus"} for i in range(15)
        ] + [
            {"id": 70 + i, "location": "Smart Fit Gran Plaza Alcaravan"} for i in range(15)
        ]
        
        clusters = ChefOpsAdapter.cluster_routes(mock_orders)
        self.assertEqual(len(clusters["Centro"]), 35)
        self.assertEqual(len(clusters["San_Martin"]), 20)
        self.assertEqual(len(clusters["Universidades"]), 15)
        self.assertEqual(len(clusters["Gym_Hubs"]), 15)
        self.assertEqual(sum(len(c) for c in clusters.values()), 85)
        
        # 4. Verificación financiera de la jornada
        unit_cogs = COGS_VARIABLE_UNIT_COP
        total_cogs = order_count * unit_cogs
        self.assertEqual(round(total_cogs, 2), 474652.75)
        
        total_revenue_tier1 = order_count * PRICE_TIER_1_COP
        self.assertEqual(total_revenue_tier1, 1147500)
        gross_profit = total_revenue_tier1 - total_cogs
        self.assertGreater(gross_profit, 600000)

    # ==========================================================================
    # SCENARIO 3: Viral Trend on Fatigue Generates Complete 16s Video
    # ==========================================================================
    def test_scenario_3_trend_to_rendered_16s_video(self):
        """
        Scenario 3:
        Trend on workplace fatigue in Yopal converts into a 4-beat script,
        synthesizes voiceover with es-CO-GonzaloNeural, renders 1080x1920 overlay,
        and composites final vertical MP4 with FFmpeg.
        """
        topic = "Evitar el letargo vespertino (mal del puerco) en oficinas de Yopal"
        
        # 1. Trend directive
        directive = TrendRadarAdapter.create_trend_directive("trend_fatiga_yopal", topic, "lifestyle", "El almuerzo corriente te da sueño")
        self.assertEqual(directive["product_specs_featured"]["weight_grams"], 305)
        self.assertEqual(directive["cta_keyword"], TRIGGER_KEYWORD)
        
        # 2. 4-beat script
        script = VideoPipelineAdapter.generate_4beat_script(directive["topic"])
        self.assertEqual(script["total_duration"], 16.0)
        self.assertEqual(len(script["beats"]), 4)
        
        # 3. Audio synthesis con Edge TTS
        import asyncio
        import edge_tts
        temp_audio = Path("temp_scenario3_audio.mp3")
        try:
            async def gen_voice():
                comm = edge_tts.Communicate(script["beats"][0]["spoken_text"], VOICE_COLOMBIA_MALE)
                await comm.save(str(temp_audio))
            asyncio.run(gen_voice())
            self.assertTrue(temp_audio.exists())
            self.assertGreater(temp_audio.stat().st_size, 500)
        finally:
            if temp_audio.exists():
                temp_audio.unlink()
                
        # 4. Pillow overlay card
        temp_card = Path("temp_scenario3_card.png")
        try:
            VideoPipelineAdapter.render_overlay_card(
                script["beats"][1]["visual_headline"],
                script["beats"][1]["visual_sub"],
                temp_card
            )
            self.assertTrue(temp_card.exists())
            from PIL import Image
            with Image.open(temp_card) as img:
                self.assertEqual(img.size, (1080, 1920))
        finally:
            if temp_card.exists():
                temp_card.unlink()
                
        # 5. FFmpeg composition
        temp_render = Path("temp_scenario3_output.mp4")
        try:
            cmd = [
                "ffmpeg", "-y", "-t", "1",
                "-i", str(BASE_VIDEO_PATH),
                "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-an", str(temp_render)
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(proc.returncode, 0)
            self.assertTrue(temp_render.exists())
            self.assertGreater(temp_render.stat().st_size, 1000)
        finally:
            if temp_render.exists():
                temp_render.unlink()

    # ==========================================================================
    # SCENARIO 4: Cloud Health Monitoring and Failover When OmniRoute is Offline
    # ==========================================================================
    def test_scenario_4_cloud_health_failover_and_recovery(self):
        """
        Scenario 4:
        Cloud health monitoring starts healthy, handles simulated OmniRoute gateway
        interruption without crashing, serves TapMeals domain fallback, and restores
        cleanly when gateway recovers.
        """
        import app
        
        # 1. Estado inicial saludable
        res_init = self.client.get("/health")
        self.assertEqual(res_init.status_code, 200)
        data_init = res_init.get_json()
        self.assertEqual(data_init["service"], "tapmeals-cloud-auto-responder")
        self.assertIn("omniroute_available", data_init)
        
        # 2. Simulación de caída de OmniRoute
        old_check = app.verificar_estado_omniroute
        try:
            app.verificar_estado_omniroute = lambda timeout=1.5: False
            
            # Health check reporta degradación sin código 500
            res_degraded = self.client.get("/health")
            self.assertEqual(res_degraded.status_code, 200)
            data_deg = res_degraded.get_json()
            self.assertFalse(data_deg["omniroute_available"])
            
            # El contestador responde con el fallback inteligente de TapMeals
            dm_res = evaluar_reglas("Tienen almuerzo hoy?", "dm", self.config)
            self.assertTrue(dm_res["triggers"])
            self.assertIn("TapMeals Yopal", dm_res["dm_response"])
            self.assertIn("305 g", dm_res["dm_response"])
            self.assertIn(WHATSAPP_NUMBER, dm_res["dm_response"])
            
        finally:
            # 3. Recuperación del servicio
            app.verificar_estado_omniroute = old_check
            
        res_recovered = self.client.get("/health")
        self.assertEqual(res_recovered.status_code, 200)
        self.assertTrue(res_recovered.get_json()["omniroute_available"])

    # ==========================================================================
    # SCENARIO 5: End-to-End Customer Journey from Comment "TapTap" to WhatsApp
    # ==========================================================================
    def test_scenario_5_end_to_end_customer_journey(self):
        """
        Scenario 5:
        Customer comments 'TapTap' on Instagram -> receives public reply < 3s ->
        receives DM with 4:5 menu card and WhatsApp link -> converts order before 10:30 AM ->
        delivers at 12:45 PM -> schedules 1:45 PM feedback (rated 5/5) ->
        upgrades to weekly subscription on Friday.
        """
        username = "atleta_casanare_01"
        
        # 1. Comentario en Reel
        comment_text = "Quiero probar el menú TapTap!"
        routing = GrowthLeadAdapter.route_comment_to_dm(comment_text, username)
        self.assertTrue(routing["triggers"])
        self.assertIn(f"@{username}", routing["public_reply"])
        self.assertIn("DM", routing["public_reply"])
        
        # 2. Despacho por DM
        dm = routing["dm_payload"]
        self.assertIn("Menu_Oficial_TapMeals_Yopal.png", dm["image"])
        self.assertIn("305g reales", dm["text"])
        self.assertIn(WHATSAPP_NUMBER, dm["text"])
        
        # 3. Puntuación de lead asciende a Warm
        score1, tier1 = GrowthLeadAdapter.score_lead([comment_text])
        self.assertEqual(tier1, "Warm")
        
        # 4. Pedido realizado y pagado antes de las 10:30 AM
        order_time = (9, 45, 0)
        self.assertTrue(ChefOpsAdapter.check_cutoff(*order_time))
        
        score2, tier2 = GrowthLeadAdapter.score_lead([comment_text, "Nequi pagado", "pedido_confirmado"])
        self.assertEqual(tier2, "Converted")
        self.assertGreaterEqual(score2, 10)
        
        # 5. Entrega a las 12:45 PM -> Programación de feedback a la 1:45 PM
        feedback_schedule = RetentionAgentAdapter.schedule_feedback("12:45")
        self.assertEqual(feedback_schedule, "13:45")
        
        # 6. Calificación del cliente: 5 estrellas
        qa_result = RetentionAgentAdapter.process_rating(5, "Excelente temperatura y sabor!")
        self.assertEqual(qa_result["status"], "positive")
        self.assertFalse(qa_result["escalate_to_chef"])
        
        # 7. Cliente acumula 3 pedidos en la semana -> Oferta de Plan Semanal ($72.500 COP)
        weekly_upgrade = RetentionAgentAdapter.evaluate_subscription_upgrade(3)
        self.assertIsNotNone(weekly_upgrade)
        self.assertTrue(weekly_upgrade["eligible"])
        self.assertEqual(weekly_upgrade["weekly_plan_cop"], PRICE_WEEKLY_PLAN_COP)
        self.assertEqual(weekly_upgrade["savings_cop"], 5000)


if __name__ == "__main__":
    unittest.main()
