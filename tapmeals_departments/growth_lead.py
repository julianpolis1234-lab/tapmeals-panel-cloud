"""
TapMeals Autonomous Operational Departments — GrowthLead
Module: tapmeals_departments.growth_lead
Handles:
- Comment-to-DM routing (<3s response contract) with public reply and rich DM payload
- Lead scoring matrix with status transitions (Cold -> Warm -> Hot -> Converted)
- Direct WhatsApp bridge integration (573202337178)
"""

from typing import List, Tuple, Dict, Any, Optional

TRIGGER_KEYWORD = "TapTap"
WHATSAPP_NUMBER = "573202337178"


def score_lead(interactions: List[str]) -> Tuple[int, str]:
    """
    Calcula puntuación acumulada de lead según interacciones y determina su categoría:
    - Converted: Pedido confirmado / pagado vía Nequi, Daviplata o confirmación explícita
    - Hot: Puntuación >= 8 (mención a WhatsApp, gimnasios como Smart Fit/Bodytech o múltiples interacciones)
    - Warm: Puntuación >= 4 (pregunta por TapTap, menú, precio)
    - Cold: Menor a 4 (solo likes, emojis o interacciones pasivas)
    """
    score = 0
    has_order = False
    
    for inter in interactions:
        low = str(inter).lower()
        if "like" in low:
            score += 1
        elif "emoji" in low:
            score += 2
        elif TRIGGER_KEYWORD.lower() in low or "precio" in low or "menu" in low:
            score += 5
        elif "whatsapp" in low or "gym" in low or "smart fit" in low or "bodytech" in low:
            score += 8
        elif "pagado" in low or "nequi" in low or "daviplata" in low or "pedido_confirmado" in low:
            score += 12
            has_order = True

    if has_order:
        tier = "Converted"
    elif score >= 8:
        tier = "Hot"
    elif score >= 4:
        tier = "Warm"
    else:
        tier = "Cold"
        
    return score, tier


def route_comment_to_dm(comment_text: str, username: str) -> Dict[str, Any]:
    """
    Procesa un comentario en menos de 3 segundos:
    Detecta 'TapTap' (case-insensitive) y genera:
    - public_reply: Respuesta pública en el Reel mencionando @usuario
    - dm_payload: Mensaje privado con especificaciones de 305g, valores y enlace de WhatsApp
    """
    triggers = TRIGGER_KEYWORD.lower() in comment_text.lower()
    
    if triggers:
        public_reply = f"@{username} ¡Te acabamos de enviar el menú oficial por DM! Revisa tu bandeja 🍱⚡"
        dm_text = (
            f"¡Hola @{username}! 🍱⚡ Aquí tienes el menú oficial de TapMeals Yopal.\n"
            f"305g reales en báscula: 150g pechuga, 80g arroz, 75g vegetales.\n"
            f"Valores: $13.500 - $15.000 COP.\n"
            f"Pide aquí: https://wa.me/{WHATSAPP_NUMBER}?text=Hola%20TapMeals,%20vengo%20de%20Instagram"
        )
        dm_payload = {
            "image": "Menu_Oficial_TapMeals_Yopal.png",
            "text": dm_text,
            "whatsapp_url": f"https://wa.me/{WHATSAPP_NUMBER}"
        }
    else:
        public_reply = None
        dm_payload = None

    return {
        "triggers": triggers,
        "public_reply": public_reply,
        "dm_payload": dm_payload
    }
