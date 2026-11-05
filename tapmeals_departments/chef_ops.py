"""
TapMeals Autonomous Operational Departments — ChefOps
Module: tapmeals_departments.chef_ops
Handles:
- 10:30 AM Cutoff reconciliation
- MRP calculation with 30% shrinkage for raw chicken, dry rice, vegetable trio breakdown, and BOPS containers
- Route clustering across 4 delivery zones in Yopal (Centro, San Martin, Universidades, Gym Hubs)
"""

from typing import Dict, Any, List

CUTOFF_HOUR = 10
CUTOFF_MINUTE = 30

PORTION_CHICKEN_GRAMS = 150
PORTION_RICE_GRAMS = 80
PORTION_VEG_GRAMS = 75
PORTION_BROCCOLI_GRAMS = 25
PORTION_TOMATO_GRAMS = 25
PORTION_CARROT_GRAMS = 25
TOTAL_BOWL_WEIGHT_GRAMS = 305

CHICKEN_SHRINKAGE_RATE = 0.30  # 30% coccion


def check_cutoff(hour: int, minute: int, second: int = 0) -> bool:
    """
    Retorna True si el pedido entra dentro del corte diario (<= 10:30:00).
    Pedidos posteriores a las 10:30:00 se difieren para el siguiente turno.
    """
    if hour < CUTOFF_HOUR:
        return True
    if hour == CUTOFF_HOUR:
        if minute < CUTOFF_MINUTE:
            return True
        if minute == CUTOFF_MINUTE and second == 0:
            return True
    return False


def calculate_mrp(order_count: int) -> Dict[str, Any]:
    """
    Calcula explosión de materiales crudos (MRP) para N pedidos.
    Aplica merma de cocción del 30% en pechuga de pollo y desglosa vegetales.
    """
    if order_count < 0:
        raise ValueError("Order count cannot be negative")

    raw_chicken = round(order_count * (PORTION_CHICKEN_GRAMS / 1000.0) / (1.0 - CHICKEN_SHRINKAGE_RATE), 3)
    dry_rice = round(order_count * (PORTION_RICE_GRAMS / 1000.0), 3)
    raw_veg = round(order_count * (PORTION_VEG_GRAMS / 1000.0), 3)
    broccoli = round(order_count * (PORTION_BROCCOLI_GRAMS / 1000.0), 3)
    tomato = round(order_count * (PORTION_TOMATO_GRAMS / 1000.0), 3)
    carrot = round(order_count * (PORTION_CARROT_GRAMS / 1000.0), 3)
    bops_containers = order_count

    alerts = []
    if raw_chicken < 5.0 and order_count > 0:
        alerts.append("LOW_CHICKEN_STOCK")
    if bops_containers < 50 and order_count > 0:
        alerts.append("LOW_CONTAINER_STOCK")

    return {
        "order_count": order_count,
        "raw_chicken_kg": raw_chicken,
        "dry_rice_kg": dry_rice,
        "vegetables_total_kg": raw_veg,
        "vegetables_breakdown_kg": {
            "broccoli": broccoli,
            "tomato": tomato,
            "carrot": carrot,
        },
        "bops_containers_units": bops_containers,
        "alerts": alerts,
    }


def cluster_routes(orders: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Agrupa pedidos en 4 clusters logísticos de Yopal:
    - Centro (bancos, oficinas gubernamentales, alcaldía)
    - San_Martin (campiña, alameda, hobos)
    - Universidades (Unitrópico, Unisangil, SENA)
    - Gym_Hubs (Smart Fit, Bodytech, boxes y centros fitness)
    """
    clusters = {
        "Centro": [],
        "San_Martin": [],
        "Universidades": [],
        "Gym_Hubs": [],
    }
    for ord_item in orders:
        loc = (ord_item.get("location") or "").lower()
        if any(k in loc for k in ["centro", "alcaldia", "gobernacion", "banco"]):
            clusters["Centro"].append(ord_item)
        elif any(k in loc for k in ["san martin", "campiña", "alameda", "hobos"]):
            clusters["San_Martin"].append(ord_item)
        elif any(k in loc for k in ["unitropico", "unisangil", "sena", "universidad"]):
            clusters["Universidades"].append(ord_item)
        else:
            clusters["Gym_Hubs"].append(ord_item)
    return clusters
