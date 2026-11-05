"""
TapMeals Autonomous Operational Departments — Comprehensive M2 Unit & Integration Test Suite
Verifies genuine implementation of:
- chef_ops.py: 10:30 cutoff, MRP calculations with shrinkage, route clustering
- trend_radar.py: TrendDirective schema, active trends persistence, OmniRoute scanner
- growth_lead.py: Lead scoring transitions, comment-to-DM routing
- retention_agent.py: Feedback scheduling, rating processing, subscription upgrades
- REST API endpoints exposed in app.py (/api/departments/*)
"""

import os
import sys
import unittest
import json
import tempfile
from pathlib import Path

# Configurar path para importar desde la raíz del panel
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ["TAPMEALS_CLOUD_WORKER_ONLY"] = "1"

from tapmeals_departments.chef_ops import (
    check_cutoff,
    calculate_mrp,
    cluster_routes,
    PORTION_CHICKEN_GRAMS,
    PORTION_RICE_GRAMS,
    PORTION_VEG_GRAMS,
    TOTAL_BOWL_WEIGHT_GRAMS,
)
from tapmeals_departments.trend_radar import (
    create_trend_directive,
    save_active_trend,
    load_active_trends,
    scan_trends_omniroute,
)
from tapmeals_departments.growth_lead import (
    score_lead,
    route_comment_to_dm,
)
from tapmeals_departments.retention_agent import (
    schedule_feedback,
    process_rating,
    evaluate_subscription_upgrade,
    PRICE_WEEKLY_PLAN_COP,
    PRICE_MONTHLY_PLAN_COP,
)


class TestChefOps(unittest.TestCase):
    """Pruebas unitarias para operaciones de cocina y MRP."""

    def test_cutoff_boundaries(self):
        # Antes de las 10:30
        self.assertTrue(check_cutoff(9, 45, 0))
        self.assertTrue(check_cutoff(10, 29, 59))
        self.assertTrue(check_cutoff(10, 30, 0))
        # Después de las 10:30
        self.assertFalse(check_cutoff(10, 30, 1))
        self.assertFalse(check_cutoff(10, 31, 0))
        self.assertFalse(check_cutoff(11, 0, 0))
        self.assertFalse(check_cutoff(13, 15, 0))

    def test_mrp_negative_count_raises(self):
        with self.assertRaises(ValueError):
            calculate_mrp(-5)

    def test_mrp_zero_orders(self):
        mrp = calculate_mrp(0)
        self.assertEqual(mrp["order_count"], 0)
        self.assertEqual(mrp["raw_chicken_kg"], 0.0)
        self.assertEqual(mrp["dry_rice_kg"], 0.0)
        self.assertEqual(mrp["vegetables_total_kg"], 0.0)
        self.assertEqual(len(mrp["alerts"]), 0)

    def test_mrp_100_orders_precision(self):
        mrp = calculate_mrp(100)
        self.assertAlmostEqual(mrp["raw_chicken_kg"], 21.429, places=2)
        self.assertEqual(mrp["dry_rice_kg"], 8.0)
        self.assertEqual(mrp["vegetables_total_kg"], 7.5)
        self.assertEqual(mrp["vegetables_breakdown_kg"]["broccoli"], 2.5)
        self.assertEqual(mrp["vegetables_breakdown_kg"]["tomato"], 2.5)
        self.assertEqual(mrp["vegetables_breakdown_kg"]["carrot"], 2.5)
        self.assertEqual(mrp["bops_containers_units"], 100)
        self.assertEqual(mrp["alerts"], [])

    def test_mrp_low_stock_alerts(self):
        mrp = calculate_mrp(10)
        self.assertIn("LOW_CHICKEN_STOCK", mrp["alerts"])
        self.assertIn("LOW_CONTAINER_STOCK", mrp["alerts"])

    def test_route_clustering(self):
        sample_orders = [
            {"id": "o1", "location": "Edificio Gobernación de Casanare Centro"},
            {"id": "o2", "location": "Barrio San Martin cerca a la alameda"},
            {"id": "o3", "location": "Campus Unitropico porteria"},
            {"id": "o4", "location": "Smart Fit Yopal sede alcaravan"},
            {"id": "o5", "location": "Crossfit Box Yopal"},
        ]
        clusters = cluster_routes(sample_orders)
        self.assertEqual(len(clusters["Centro"]), 1)
        self.assertEqual(len(clusters["San_Martin"]), 1)
        self.assertEqual(len(clusters["Universidades"]), 1)
        self.assertEqual(len(clusters["Gym_Hubs"]), 2)


class TestTrendRadar(unittest.TestCase):
    """Pruebas unitarias para inteligencia de mercado y TrendRadar."""

    def test_directive_schema(self):
        directive = create_trend_directive(
            "t_test_01",
            "Fatiga en oficinas de Yopal",
            "lifestyle",
            "¿Te da sueño a las 2PM por almorzar frito?"
        )
        self.assertEqual(directive["trend_id"], "t_test_01")
        self.assertEqual(directive["cta_keyword"], "TapTap")
        self.assertEqual(directive["product_specs_featured"]["weight_grams"], 305)
        self.assertEqual(directive["product_specs_featured"]["chicken_grams"], 150)
        self.assertIn("13.500", directive["product_specs_featured"]["price_cop"])
        self.assertIn("573202337178", directive["whatsapp_link"])

    def test_save_and_load_active_trends(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name
        try:
            d1 = create_trend_directive("trend_x1", "Topic 1", "fitness", "Hook 1")
            save_active_trend(d1, filepath=temp_path)
            loaded = load_active_trends(filepath=temp_path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["trend_id"], "trend_x1")

            # Update existing
            d1_updated = create_trend_directive("trend_x1", "Topic 1 Updated", "fitness", "Hook 1 New")
            save_active_trend(d1_updated, filepath=temp_path)
            loaded2 = load_active_trends(filepath=temp_path)
            self.assertEqual(len(loaded2), 1)
            self.assertEqual(loaded2[0]["topic"], "Topic 1 Updated")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_scan_trends_omniroute_fallback(self):
        directive = scan_trends_omniroute(focus_topic="rendimiento fitness")
        self.assertIn("trend_id", directive)
        self.assertIn("topic", directive)
        self.assertEqual(directive["cta_keyword"], "TapTap")


class TestGrowthLead(unittest.TestCase):
    """Pruebas unitarias para adquisición y lead scoring."""

    def test_scoring_progression(self):
        # Cold
        s1, t1 = score_lead(["like"])
        self.assertEqual(t1, "Cold")
        self.assertEqual(s1, 1)

        # Warm
        s2, t2 = score_lead(["like", "TapTap"])
        self.assertEqual(t2, "Warm")
        self.assertEqual(s2, 6)

        # Hot
        s3, t3 = score_lead(["TapTap", "Smart Fit"])
        self.assertEqual(t3, "Hot")
        self.assertEqual(s3, 13)

        # Converted
        s4, t4 = score_lead(["TapTap", "Nequi pagado", "pedido_confirmado"])
        self.assertEqual(t4, "Converted")
        self.assertGreaterEqual(s4, 12)

    def test_route_comment_triggers(self):
        res = route_comment_to_dm("Hola quiero el menu TapTap", "atleta_1")
        self.assertTrue(res["triggers"])
        self.assertIn("@atleta_1", res["public_reply"])
        self.assertIn("305g", res["dm_payload"]["text"])
        self.assertIn("150g pechuga", res["dm_payload"]["text"])
        self.assertIn("573202337178", res["dm_payload"]["whatsapp_url"])

    def test_route_comment_no_trigger(self):
        res = route_comment_to_dm("Excelente foto amigo", "usuario_random")
        self.assertFalse(res["triggers"])
        self.assertIsNone(res["public_reply"])
        self.assertIsNone(res["dm_payload"])


class TestRetentionAgent(unittest.TestCase):
    """Pruebas unitarias para post-venta y retención."""

    def test_schedule_feedback(self):
        time_str = schedule_feedback("12:30")
        self.assertEqual(time_str, "13:45")

    def test_rating_escalation_rules(self):
        # 1-3 estrellas -> alerta y escalamiento
        for r in [1, 2, 3]:
            res = process_rating(r, "Demora en entrega")
            self.assertTrue(res["escalate_to_chef"])
            self.assertEqual(res["status"], "alert")
            self.assertEqual(res["action"], "winback_resolution")

        # 4-5 estrellas -> positivo
        for r in [4, 5]:
            res = process_rating(r, "Excelente sabor")
            self.assertFalse(res["escalate_to_chef"])
            self.assertEqual(res["status"], "positive")
            self.assertEqual(res["action"], "loyalty_recorded")

    def test_subscription_upgrade_thresholds(self):
        # < 2 pedidos -> no califica
        self.assertIsNone(evaluate_subscription_upgrade(0))
        self.assertIsNone(evaluate_subscription_upgrade(1))

        # >= 2 pedidos -> califica
        offer = evaluate_subscription_upgrade(2)
        self.assertIsNotNone(offer)
        self.assertTrue(offer["eligible"])
        self.assertEqual(offer["weekly_plan_cop"], PRICE_WEEKLY_PLAN_COP)
        self.assertEqual(offer["monthly_plan_cop"], PRICE_MONTHLY_PLAN_COP)
        self.assertEqual(offer["savings_cop"], 5000)


class TestDepartmentRestEndpoints(unittest.TestCase):
    """Pruebas de integración sobre los endpoints REST de app.py."""

    @classmethod
    def setUpClass(cls):
        from app import app
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_chef_ops_mrp_endpoint(self):
        res = self.client.post("/api/departments/chef-ops/mrp", json={"order_count": 80})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("raw_chicken_kg", data)
        self.assertEqual(data["bops_containers_units"], 80)

    def test_chef_ops_mrp_invalid_input(self):
        res = self.client.post("/api/departments/chef-ops/mrp", json={"order_count": -1})
        self.assertEqual(res.status_code, 400)

    def test_chef_ops_cutoff_endpoint(self):
        res = self.client.get("/api/departments/chef-ops/cutoff")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["cutoff_time"], "10:30:00")
        self.assertIn("cutoff_passed", data)

    def test_trends_endpoints(self):
        res = self.client.get("/api/departments/trends")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIsInstance(data.get("trends"), list)

        # Scan endpoint
        res_scan = self.client.post("/api/departments/trends/scan", json={"topic": "Almuerzo fitness en Yopal"})
        self.assertEqual(res_scan.status_code, 200)
        data_scan = res_scan.get_json()
        self.assertTrue(data_scan.get("success"))
        self.assertIn("directive", data_scan)

    def test_leads_endpoints(self):
        # Score
        res_score = self.client.post("/api/departments/leads/score", json={"interactions": ["like", "TapTap"]})
        self.assertEqual(res_score.status_code, 200)
        data_score = res_score.get_json()
        self.assertEqual(data_score["tier"], "Warm")

        # Route
        res_route = self.client.post("/api/departments/leads/route", json={"comment_text": "Quiero TapTap", "username": "juan"})
        self.assertEqual(res_route.status_code, 200)
        data_route = res_route.get_json()
        self.assertTrue(data_route["triggers"])
        self.assertIn("@juan", data_route["public_reply"])

    def test_retention_endpoint(self):
        res = self.client.post("/api/departments/retention/feedback", json={"rating": 2, "feedback": "Llegó frío"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["escalate_to_chef"])
        self.assertEqual(data["status"], "alert")

    def test_departments_status_endpoint(self):
        res = self.client.get("/api/departments/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("departments_active"), 4)
        self.assertIn("chef_ops", data["departments"])
        self.assertIn("trend_radar", data["departments"])
        self.assertIn("growth_lead", data["departments"])
        self.assertIn("retention_agent", data["departments"])


if __name__ == "__main__":
    unittest.main()
