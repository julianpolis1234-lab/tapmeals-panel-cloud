"""
TapMeals Autonomous Operational Departments — TrendRadar
Module: tapmeals_departments.trend_radar
Handles:
- TrendDirective standardization with verified product specifications (305g, 150g chicken, $13.500-$15.000 COP, BOPS 3 divisiones)
- OmniRoute Claude Sonnet 5.5 integration for Yopal fitness/nutrition trend scanning
- Persistence and loading of active trends in data/active_trends.json
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

WHATSAPP_NUMBER = "573202337178"
TRIGGER_KEYWORD = "TapTap"
TOTAL_BOWL_WEIGHT_GRAMS = 305
PORTION_CHICKEN_GRAMS = 150
PRICE_TIER_1_COP = 13500
PRICE_TIER_2_COP = 15000

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BASE_DIR / "data"
DEFAULT_TRENDS_FILE = DEFAULT_DATA_DIR / "active_trends.json"


def _resolve_path(filepath: str) -> Path:
    p = Path(filepath)
    if not p.is_absolute():
        p = BASE_DIR / filepath
    return p


def create_trend_directive(
    trend_id: str,
    topic: str,
    category: str,
    hook_angle: str
) -> Dict[str, Any]:
    """
    Crea una directiva estandarizada según el esquema oficial en PROJECT.md.
    Incluye especificaciones verificadas de 305g y link de WhatsApp oficial.
    """
    price_str = f"${PRICE_TIER_1_COP:,} - ${PRICE_TIER_2_COP:,} COP".replace(",", ".")
    return {
        "trend_id": trend_id,
        "topic": topic,
        "category": category,
        "hook_angle": hook_angle,
        "product_specs_featured": {
            "weight_grams": TOTAL_BOWL_WEIGHT_GRAMS,
            "chicken_grams": PORTION_CHICKEN_GRAMS,
            "price_cop": price_str,
            "packaging": "BOPS 3 divisiones"
        },
        "whatsapp_link": f"https://wa.me/{WHATSAPP_NUMBER}?text=Hola%20TapMeals!%20Vi%20el%20video%20de%20{topic}",
        "cta_keyword": TRIGGER_KEYWORD
    }


def save_active_trend(directive: Dict[str, Any], filepath: str = "data/active_trends.json") -> bool:
    """
    Persiste una directiva de tendencia activa en el archivo especificado.
    Si ya existe una directiva con el mismo trend_id, la actualiza; de lo contrario, la agrega.
    """
    target = _resolve_path(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)
    
    current_trends = load_active_trends(filepath=filepath)
    
    updated = False
    for i, t in enumerate(current_trends):
        if t.get("trend_id") == directive.get("trend_id"):
            current_trends[i] = directive
            updated = True
            break
            
    if not updated:
        current_trends.append(directive)
        
    try:
        target.write_text(json.dumps(current_trends, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[TrendRadar] Error guardando active_trends: {e}")
        return False


def load_active_trends(filepath: str = "data/active_trends.json") -> List[Dict[str, Any]]:
    """
    Carga las directivas de tendencias activas desde disco.
    Si el archivo no existe o está vacío, devuelve lista vacía si es ruta personalizada,
    o lista predeterminada con dolores fitness de Yopal para el archivo global.
    """
    target = _resolve_path(filepath)
    if target.exists():
        try:
            content = target.read_text(encoding="utf-8").strip()
            if not content:
                return []
            data = json.loads(content)
            if isinstance(data, list):
                return data
        except Exception as e:
            print(f"[TrendRadar] Error leyendo active_trends: {e}")
            if filepath != "data/active_trends.json":
                return []

    if filepath != "data/active_trends.json":
        return []

    # Fallback predeterminado con 3 dolores fitness locales de Yopal
    default_trends = [
        create_trend_directive(
            "trend_fatiga_yopal",
            "Fatiga de oficina y sopas grasosas",
            "lifestyle",
            "¿Cansado del almuerzo corriente y grasoso en el centro de Yopal que te tumba a las 2PM?"
        ),
        create_trend_directive(
            "trend_smartfit_macros",
            "Proteína exacta post-entreno en Smart Fit",
            "fitness",
            "¿Entrenas en Smart Fit o Bodytech Yopal? 150g de pechuga real pesada en báscula digital."
        ),
        create_trend_directive(
            "trend_tiempo_oficinas",
            "Almuerzo fit en tu oficina antes de las 12",
            "productividad",
            "Tu almuerzo fitness en envase hermético BOPS de 3 divisiones listo en tu escritorio."
        )
    ]
    return default_trends


def scan_trends_omniroute(
    focus_topic: str = "fitness y nutricion en Yopal",
    model: str = "claude"
) -> Dict[str, Any]:
    """
    Escanea tendencias y pain points de atletas/oficinistas en Yopal consultando OmniRoute (Claude Sonnet 5.5).
    Genera y almacena una directiva estandarizada.
    """
    try:
        from omniroute_client import consultar_omniroute
        prompt = (
            f"Actúa como TrendRadar para TapMeals en Yopal, Casanare. "
            f"Analiza la siguiente temática: '{focus_topic}'. "
            f"Detecta un dolor puntual de los clientes en Yopal (ej. fatiga después de almorzar, "
            f"comida corriente con aceite quemado, falta de proteína post-gimnasio en Smart Fit o Bodytech). "
            f"Responde estrictamente en formato JSON con la siguiente estructura:\n"
            f'{{"topic": "Nombre breve del tema", "category": "fitness|lifestyle|nutricion", "hook_angle": "Gancho conversacional con modismos colombianos sutiles"}}'
        )
        res = consultar_omniroute(prompt=prompt, model=model, timeout=12)
        
        topic = "Evitar fatiga post-almuerzo en Yopal"
        category = "lifestyle"
        hook_angle = "¿Te da pesadez a las 2PM por almorzar fritos en el centro de Yopal? Pide 305g limpios con TapMeals."
        
        if res.get("success") and res.get("response"):
            raw_text = res["response"]
            m = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                    topic = parsed.get("topic", topic)
                    category = parsed.get("category", category)
                    hook_angle = parsed.get("hook_angle", hook_angle)
                except Exception:
                    pass
    except Exception as e:
        print(f"[TrendRadar] OmniRoute no disponible, usando dolor local de Yopal: {e}")
        topic = "Evitar fatiga de oficina"
        category = "lifestyle"
        hook_angle = "El almuerzo corriente te da sueño en Yopal; prueba proteína limpia sin aceites."

    trend_id = f"trend_{int(time.time())}"
    directive = create_trend_directive(trend_id, topic, category, hook_angle)
    save_active_trend(directive)
    return directive
