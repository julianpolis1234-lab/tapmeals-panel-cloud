"""
TapMeals Autonomous Operational Departments — RetentionAgent
Module: tapmeals_departments.retention_agent
Handles:
- Post-delivery feedback dispatch scheduling (standard 13:45)
- QA rating processing (1-5 stars) with automatic chef escalation on ratings <= 3
- Weekly subscription upgrade qualification (Plan Semanal $72.500 COP, Plan Mensual $270.000 COP)
"""

from typing import Dict, Any, Optional

PRICE_WEEKLY_PLAN_COP = 72500   # 5 bowls ($14.500/u)
PRICE_MONTHLY_PLAN_COP = 270000 # 20 bowls ($13.500/u)
SAVINGS_WEEKLY_COP = 5000


def schedule_feedback(delivery_time_str: str = "12:15") -> str:
    """
    Calcula la hora recomendada para solicitar feedback al atleta (1:45 PM / 13:45),
    garantizando que haya terminado de almorzar sin interrumpir su jornada laboral.
    """
    # En el flujo estándar de Yopal los domicilios llegan entre 11:30 AM y 1:00 PM
    # El feedback se centraliza de manera óptima a las 13:45 (1:45 PM)
    return "13:45"


def process_rating(rating: int, feedback_text: str = "") -> Dict[str, Any]:
    """
    Procesa una calificación de 1 a 5 estrellas:
    - Rating <= 3: Activa alerta roja, escala de inmediato a ChefOps y programa resolución win-back.
    - Rating > 3: Registra satisfacción positiva y alimenta métricas de lealtad.
    """
    needs_alert = (rating <= 3)
    return {
        "rating": rating,
        "feedback_text": feedback_text,
        "status": "alert" if needs_alert else "positive",
        "escalate_to_chef": needs_alert,
        "action": "winback_resolution" if needs_alert else "loyalty_recorded"
    }


def evaluate_subscription_upgrade(order_count_this_week: int) -> Optional[Dict[str, Any]]:
    """
    Evalúa si un cliente habitual califica para migrar de compras individuales a suscripción:
    - Si ha realizado >= 2 pedidos en la semana en curso, califica al Plan Semanal con ahorro de $5.000 COP.
    - En caso contrario, retorna None (continúa en flujo individual).
    """
    if order_count_this_week >= 2:
        return {
            "eligible": True,
            "weekly_plan_cop": PRICE_WEEKLY_PLAN_COP,
            "monthly_plan_cop": PRICE_MONTHLY_PLAN_COP,
            "savings_cop": SAVINGS_WEEKLY_COP,
            "offer_text": f"¡Ahorra en tus almuerzos fitness! Plan Semanal por ${PRICE_WEEKLY_PLAN_COP:,} COP.".replace(",", ".")
        }
    return None
