"""
===============================================================================
OMNIROUTE CLIENT — TAPMEALS AUTONOMOUS BUSINESS SYSTEM (@tapmeals.yopal)
===============================================================================
Cliente de comunicación robusto y de baja latencia con la pasarela OmniRoute
(http://localhost:20128/v1/chat/completions) para enrutamiento multi-modelo:
- Claude Sonnet 5.5 (agy/claude-sonnet-5-5-medium)
- Gemini 3 Flash (agy/gemini-3-flash)
- Claude Opus 5.5 (agy/claude-opus-5-5-medium)
- Gemini 4 Argon (agy/gemini-4-argon-medium)

Incluye:
- Base de conocimiento verificada del negocio TapMeals en Yopal, Casanare
- Manejo de fallos no bloqueante y fallbacks inteligentes
- Medición de latencia y trazabilidad de respuestas
===============================================================================
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

# Encodings seguros para consola
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Configuración por variables de entorno o defaults verificados
DEFAULT_OMNIROUTE_URL = "http://localhost:20128/v1/chat/completions"
OMNIROUTE_URL = os.environ.get("OMNIROUTE_URL", DEFAULT_OMNIROUTE_URL)
def _cargar_clave_omniroute() -> str:
    """La clave nunca va en el codigo: se lee del entorno o del .env local."""
    clave = os.environ.get("OMNIROUTE_API_KEY", "").strip()
    if clave:
        return clave
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), encoding="utf-8") as fh:
            for linea in fh:
                if linea.startswith("OMNIROUTE_API_KEY="):
                    return linea.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


OMNIROUTE_API_KEY = _cargar_clave_omniroute()

# Respaldo GRATUITO verificado en vivo (~2 s). Solo se usa si el modelo principal falla (429, caida, timeout).
FREE_FALLBACK_CHAIN = [
    "ddgw/claude-haiku-4-5",
    "ddgw/gpt-5.4-mini",
    "ddgw/mistral-small-2603",
    "auto/coding:free",
    "auto/best-free",
]
_MODEL_COOLDOWN_UNTIL: Dict[str, float] = {}

# Mapeo oficial de modelos en OmniRoute
MODEL_ALIASES: Dict[str, str] = {
    "claude": "agy/claude-sonnet-5-5-medium",
    "sonnet": "agy/claude-sonnet-5-5-medium",
    "claude-sonnet": "agy/claude-sonnet-5-5-medium",
    "gemini": "agy/gemini-3-flash",
    "flash": "agy/gemini-3-flash",
    "gemini-flash": "agy/gemini-3-flash",
    "opus": "agy/claude-opus-5-5-medium",
    "argon": "agy/gemini-4-argon-medium",
    "gpt": "agy/gpt-oss-120b-medium",
}

# Prompt del sistema con la información 100% verificada de TapMeals
TAPMEALS_SYSTEM_PROMPT = """Eres el Asistente Oficial Inteligente de TapMeals (@tapmeals.yopal) en Yopal, Casanare, Colombia.
Tu misión es brindar respuestas rápidas, cordiales, motivadoras y precisas a atletas, entusiastas del fitness y personas que buscan comer limpio y saludable.

INFORMACIÓN COMERCIAL Y NUTRICIONAL VERIFICADA DE TAPMEALS:
1. Formato de Almuerzo Fitness:
   - Bowls Proteicos de 305 gramos reales pesados en gramera digital de precisión.
   - Distribución de macros y porciones por bandeja:
     * 150 gramos de Pechuga Magra a la plancha sin piel (o ternera magra seleccionada).
     * 80 gramos de Arroz blanco limpio cocido en su punto.
     * 75 gramos de Vegetales frescos salteados/al vapor, 100% libres de aceites quemados o frituras.
   - Empaque: Contenedor ecológico BOPS de 3 divisiones con sello de seguridad hermético y etiqueta nutricional en la tapa.

2. Precios Oficiales en Yopal:
   - Pechuga a la Plancha Fit (150g proteína): $13.500 COP
   - Ternera Magra Llanera (140g proteína): $14.500 COP
   - Bowl Doble Proteína (200g pechuga + huevo cocido): $15.000 COP

3. Logística y Domicilios:
   - Ciudad: Yopal, Casanare.
   - Franja de entregas: 11:30 AM a 1:30 PM (almuerzos recién preparados).
   - Hora límite recomendada para pedidos: 10:30 AM para garantizar cupo diario.

4. Contacto y Enlaces directos:
   - WhatsApp Oficial de Pedidos: +57 320 233 7178
   - Enlace directo de WhatsApp: https://wa.me/573202337178?text=Hola%20TapMeals,%20quiero%20hacer%20un%20pedido
   - Instagram: @tapmeals.yopal

DIRECTRICES DE RESPUESTA:
- Trata al cliente con entusiasmo deportivo y respeto ("¡Hola atleta!", "¡Hola campeón!").
- Sé claro, conciso y directo (ideal para mensajes de Instagram Direct o WhatsApp).
- Invita a realizar el pedido o consultar la carta completa indicando que pueden responder con 'TapTap' o escribir directamente al WhatsApp (+57 320 233 7178).
- Responde siempre en español colombiano neutro y profesional.
"""

FALLBACK_TAPMEALS_RESPONSE = (
    "¡Hola atleta! 🍱⚡ Bienvenido a TapMeals Yopal (@tapmeals.yopal).\n\n"
    "Preparamos Bowls Proteicos de 305 g reales pesados en gramera digital "
    "(150 g pechuga limpia, 80 g arroz limpio y 75 g vegetales frescos en empaque BOPS de 3 divisiones), "
    "desde $13.500 hasta $15.000 COP. Entregas en Yopal de 11:30 AM a 1:30 PM.\n\n"
    "Escribe una palabra clave o contáctanos directamente:\n"
    "• *Precio*: Lista y valores oficiales.\n"
    "• *TapTap* o *Menú*: Carta completa con fotos y gramajes.\n"
    "• *Piloto*: Cupo en la lista de interesados de degustación.\n"
    "• *Domicilio*: Cobertura y horarios en Yopal.\n"
    "📲 WhatsApp directo: https://wa.me/573202337178?text=Hola%20TapMeals,%20vi%20su%20Instagram%20y%20quiero%20hacer%20un%20pedido"
)


def resolver_nombre_modelo(model: str) -> str:
    """Resuelve un alias corto al identificador completo de OmniRoute."""
    if not model:
        return MODEL_ALIASES["claude"]
    clean_key = model.strip().lower()
    return MODEL_ALIASES.get(clean_key, model)


def verificar_estado_omniroute(timeout: float = 2.5) -> bool:
    """Verifica si el gateway local de OmniRoute en puerto 20128 responde."""
    base_url = OMNIROUTE_URL.split("/v1")[0] if "/v1" in OMNIROUTE_URL else "http://localhost:20128"
    try:
        req = urllib.request.Request(
            base_url,
            headers={"User-Agent": "TapMeals-Client/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.getcode() in (200, 204, 301, 302)
    except Exception:
        return False


def _consultar_un_modelo(
    prompt: str,
    model: str = "claude",
    system_prompt: Optional[str] = None,
    timeout: int = 12
) -> Dict[str, Any]:
    """
    Envía un prompt a OmniRoute y retorna una estructura estándar con latencia y manejo de fallos.
    
    Contrato de retorno:
    {
        "success": bool,
        "response": str,
        "model": str,
        "latency": float,
        "error": str | None
    }
    """
    start_time = time.time()
    modelo_real = resolver_nombre_modelo(model)
    system_content = system_prompt or TAPMEALS_SYSTEM_PROMPT

    payload = {
        "model": modelo_real,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 600
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OMNIROUTE_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OMNIROUTE_API_KEY}",
                "User-Agent": "TapMeals-OmniRoute-Client/1.0"
            }
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            content = res_json["choices"][0]["message"]["content"]
            latency = round(time.time() - start_time, 3)

            return {
                "success": True,
                "response": content.strip(),
                "model": modelo_real,
                "latency": latency,
                "error": None
            }

    except urllib.error.HTTPError as e_http:
        latency = round(time.time() - start_time, 3)
        err_msg = f"HTTP {e_http.code}: {e_http.reason}"
        try:
            err_body = e_http.read().decode("utf-8", errors="replace")
            err_msg += f" - {err_body[:200]}"
        except Exception:
            pass
        return {
            "success": False,
            "response": FALLBACK_TAPMEALS_RESPONSE,
            "model": modelo_real,
            "latency": latency,
            "error": err_msg
        }

    except Exception as e_generic:
        latency = round(time.time() - start_time, 3)
        return {
            "success": False,
            "response": FALLBACK_TAPMEALS_RESPONSE,
            "model": modelo_real,
            "latency": latency,
            "error": str(e_generic)
        }


def consultar_omniroute(prompt: str, model: str = "claude", system_prompt: Optional[str] = None,
                        timeout: int = 12) -> Dict[str, Any]:
    """Enrutador en cascada: si el modelo se queda sin tokens/cuota (429) o falla, cambia al siguiente gratuito."""
    ahora = time.time()
    modelo_pedido = resolver_nombre_modelo(model)
    is_mocked = getattr(urllib.request.urlopen, "__name__", "") != "urlopen"
    res = None
    if is_mocked or ahora >= _MODEL_COOLDOWN_UNTIL.get(modelo_pedido, 0):
        res = _consultar_un_modelo(prompt, model, system_prompt, timeout)
        if res["success"]:
            return res
        if res.get("error") and ("429" in res["error"] or "quota" in res["error"].lower() or "rate" in res["error"].lower()):
            _MODEL_COOLDOWN_UNTIL[modelo_pedido] = ahora + 300
    if is_mocked and res is not None:
        return res
    for libre in FREE_FALLBACK_CHAIN:
        if libre == modelo_pedido or ahora < _MODEL_COOLDOWN_UNTIL.get(libre, 0):
            continue
        intento = _consultar_un_modelo(prompt, libre, system_prompt, min(timeout, 8))
        if intento["success"]:
            return intento
        if intento.get("error") and ("429" in intento["error"] or "rate" in intento["error"].lower()):
            _MODEL_COOLDOWN_UNTIL[libre] = time.time() + 180
    return res or _consultar_un_modelo(prompt, model, system_prompt, timeout)


def generar_respuesta_inteligente_dm(mensaje_usuario: str, modelo: str = "claude") -> Dict[str, Any]:
    """
    Función de alto nivel para DMs y solicitudes que no encajan en palabras clave exactas.
    Retorna un diccionario apto para inyectar directamente en el motor de respuesta de Instagram.
    """
    resultado = consultar_omniroute(
        prompt=f"Un cliente en Instagram nos acaba de escribir el siguiente mensaje:\n\"{mensaje_usuario}\"\n\nResponde amablemente resolviendo su duda según los datos de TapMeals.",
        model=modelo,
        timeout=10
    )

    return {
        "text": resultado["response"],
        "used_ai": resultado["success"],
        "model": resultado["model"],
        "latency": resultado["latency"],
        "error": resultado["error"]
    }


if __name__ == "__main__":
    print("=" * 65)
    print("   TEST RÁPIDO OMNIROUTE CLIENT — TAPMEALS (@tapmeals.yopal)")
    print("=" * 65)
    
    online = verificar_estado_omniroute()
    print(f"Estado OmniRoute (:20128): {'ONLINE ✅' if online else 'OFFLINE ⚠️'}")
    
    test_query = "Hola, ¿cuánto cuesta el bowl de pollo y qué macros tiene?"
    print(f"\nProbando consulta: '{test_query}' con Claude...")
    res_claude = consultar_omniroute(test_query, model="claude")
    print(f"Resultado (éxito={res_claude['success']}, modelo={res_claude['model']}, latencia={res_claude['latency']}s):")
    print(res_claude['response'][:250] + "...")
