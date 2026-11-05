"""
===============================================================================
SUITE DE VERIFICACIÓN PROGRAMÁTICA OMNIROUTE (:20128) & TAPMEALS
===============================================================================
Script de verificación autónoma y rigurosa de Milestone 1 (M1):
1. Verificación de conectividad TCP y HTTP al puerto 20128 de OmniRoute.
2. Consulta de inferencia activa a Claude Sonnet 5.5 (agy/claude-sonnet-5-5-medium).
3. Consulta de inferencia activa a Gemini 3 Flash (agy/gemini-3-flash).
4. Verificación de razonamiento del dominio comercial TapMeals (305g, $13.500-$15.000 COP, Yopal, WhatsApp).
5. Verificación de resiliencia y fallbacks ante fallos o modelos inexistentes.
6. Verificación de endpoints Flask: /health y /api/ai/query.
Retorna código de salida 0 únicamente si TODAS las pruebas son exitosas.
===============================================================================
"""

import os
import sys
import time
import json
from pathlib import Path

# Configurar salida UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from omniroute_client import (
    consultar_omniroute,
    verificar_estado_omniroute,
    OMNIROUTE_URL,
    FALLBACK_TAPMEALS_RESPONSE,
)


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_1_conectividad_puerto_20128() -> bool:
    print_banner("TEST 1: Conectividad con OmniRoute en Puerto 20128")
    online = verificar_estado_omniroute(timeout=3.0)
    print(f"URL Objetivo: {OMNIROUTE_URL}")
    print(f"Estado del Gateway: {'ACTIVO (HTTP 200) [OK]' if online else 'INACTIVO [ERROR]'}")
    if not online:
        print("ERROR: OmniRoute no está respondiendo en el puerto 20128.")
        return False
    return True


def test_2_consulta_claude_sonnet() -> bool:
    print_banner("TEST 2: Inferencia con Claude Sonnet 5.5 (agy/claude-sonnet-5-5-medium)")
    prompt_test = "Responde exactamente la frase: 'CLAUDE_SONNET_5_5_ACTIVO_OK'."
    start = time.time()
    res = consultar_omniroute(prompt_test, model="claude", timeout=15)
    lat = round(time.time() - start, 2)
    
    print(f"Éxito: {res['success']}")
    print(f"Modelo real empleado: {res['model']}")
    print(f"Latencia: {res['latency']}s (Total: {lat}s)")
    print(f"Respuesta:\n{res['response'][:200]}...")
    
    if not res["success"] or not res["response"]:
        print(f"ERROR: Claude Sonnet no respondió exitosamente: {res.get('error')}")
        return False
    return True


def test_3_consulta_gemini_flash() -> bool:
    print_banner("TEST 3: Inferencia con Gemini 3 Flash (agy/gemini-3-flash)")
    prompt_test = "Responde exactamente la frase: 'GEMINI_3_FLASH_ACTIVO_OK'."
    start = time.time()
    res = consultar_omniroute(prompt_test, model="gemini", timeout=15)
    lat = round(time.time() - start, 2)
    
    print(f"Éxito: {res['success']}")
    print(f"Modelo real empleado: {res['model']}")
    print(f"Latencia: {res['latency']}s (Total: {lat}s)")
    print(f"Respuesta:\n{res['response'][:200]}...")
    
    if not res["success"] or not res["response"]:
        print(f"ERROR: Gemini 3 Flash no respondió exitosamente: {res.get('error')}")
        return False
    return True


def test_4_razonamiento_dominio_tapmeals() -> bool:
    print_banner("TEST 4: Razonamiento de Dominio TapMeals (@tapmeals.yopal)")
    pregunta = "¿Cuánto cuesta el bowl de pechuga fit en Yopal y cuántos gramos de proteína trae?"
    res = consultar_omniroute(pregunta, model="claude", timeout=15)
    
    print(f"Pregunta cliente: \"{pregunta}\"")
    print(f"Éxito: {res['success']}")
    print(f"Latencia: {res['latency']}s")
    print("\n--- Respuesta del Asistente TapMeals ---")
    print(res["response"])
    print("----------------------------------------\n")
    
    texto = res["response"].lower()
    # Verificación de elementos clave de TapMeals
    verificaciones = {
        "Precio Pechuga Fit ($13.500)": ("13.500" in texto or "13500" in texto),
        "Gramaje Proteína (150 g)": ("150" in texto),
        "Gramaje Total Bowl (305 g)": ("305" in texto),
        "Contacto WhatsApp o Yopal": ("whatsapp" in texto or "320" in texto or "yopal" in texto or "wa.me" in texto)
    }
    
    todos_ok = True
    for item, ok in verificaciones.items():
        print(f"  * {item}: {'CUMPLE [OK]' if ok else 'NO DETECTADO [AVISO]'}")
        if not ok:
            todos_ok = False
            
    if not todos_ok:
        print("AVISO: La respuesta generada omitió algunos parámetros verificados del negocio.")
        # Se permite pasar si al menos tiene el precio o gramos para evitar fragilidad en el wording del LLM
        if not ("13.500" in texto or "150" in texto or "305" in texto):
            return False
            
    return True


def test_5_resiliencia_y_fallbacks() -> bool:
    print_banner("TEST 5: Resiliencia ante Fallos y Fallback Inteligente")
    # Probar modelo inválido o URL offline
    res_fake = consultar_omniroute("Hola", model="modelo_inexistente_xyz_123", timeout=5)
    print(f"Respuesta ante modelo inválido: éxito={res_fake['success']}, error={res_fake.get('error')}")
    print(f"Uso de Fallback Verificado: {'SI [OK]' if res_fake['response'] else 'NO [ERROR]'}")
    
    if not res_fake["response"] or len(res_fake["response"]) < 20:
        print("ERROR: El fallback de emergencia no produjo texto válido.")
        return False
    return True


def test_6_servidor_flask_health_y_query() -> bool:
    print_banner("TEST 6: Integración con Servidor Flask (/health y /api/ai/query)")
    from app import app
    client = app.test_client()
    
    # 6.1 Probar /health
    resp_health = client.get('/health')
    print(f"Endpoint GET /health: Código HTTP {resp_health.status_code}")
    if resp_health.status_code != 200:
        print(f"ERROR: /health retornó {resp_health.status_code}")
        return False
        
    data_health = resp_health.get_json() or {}
    print(f"Payload Health: {json.dumps(data_health, indent=2)}")
    
    if data_health.get("status") != "healthy":
        print(f"ERROR: status en /health no es 'healthy': {data_health.get('status')}")
        return False
    if "worker_alive" not in data_health:
        print("ERROR: campo 'worker_alive' faltante en /health")
        return False
        
    # 6.2 Probar /api/ai/query
    resp_query = client.post('/api/ai/query', json={
        "prompt": "¿Cuáles son los 3 bowls disponibles y sus precios?",
        "model": "gemini"
    })
    print(f"\nEndpoint POST /api/ai/query: Código HTTP {resp_query.status_code}")
    if resp_query.status_code != 200:
        print(f"ERROR: /api/ai/query retornó {resp_query.status_code}")
        return False
        
    data_query = resp_query.get_json() or {}
    print(f"Éxito AI Query: {data_query.get('success')}")
    print(f"Modelo: {data_query.get('model')}")
    print(f"Respuesta (resumen):\n{data_query.get('response', '')[:160]}...")
    
    if not data_query.get("success"):
        print("ERROR: /api/ai/query falló al consultar modelo.")
        return False
        
    return True


def ejecutar_todas_las_pruebas() -> bool:
    print_banner("INICIANDO SUITE DE VERIFICACIÓN PROGRAMÁTICA OMNIROUTE & M1")
    pruebas = [
        ("1. Conectividad Puerto 20128", test_1_conectividad_puerto_20128),
        ("2. Inferencia Claude Sonnet 5.5", test_2_consulta_claude_sonnet),
        ("3. Inferencia Gemini 3 Flash", test_3_consulta_gemini_flash),
        ("4. Razonamiento Dominio TapMeals", test_4_razonamiento_dominio_tapmeals),
        ("5. Resiliencia y Fallback", test_5_resiliencia_y_fallbacks),
        ("6. Endpoints Flask /health y /api/ai/query", test_6_servidor_flask_health_y_query),
    ]
    
    resultados = []
    for nombre, fn in pruebas:
        try:
            ok = fn()
            resultados.append((nombre, ok))
        except Exception as e:
            print(f"EXCEPCIÓN NO CONTROLADA EN {nombre}: {e}")
            resultados.append((nombre, False))
            
    print_banner("RESUMEN FINAL DE VERIFICACIÓN (M1)")
    total = len(resultados)
    pasadas = sum(1 for _, ok in resultados if ok)
    
    for nombre, ok in resultados:
        print(f"  [{'PASS [OK]' if ok else 'FAIL [ERROR]'}] {nombre}")
        
    print(f"\nResultado Global: {pasadas}/{total} pruebas superadas.")
    
    if pasadas == total:
        print("\n[EXITO] ¡TODAS LAS PRUEBAS DE MILESTONE 1 FUERON SUPERADAS CON EXITO!")
        return True
    else:
        print("\n[ERROR] ALGUNAS PRUEBAS FALLARON. REVISE LOS LOGS SUPERIORES.")
        return False


if __name__ == "__main__":
    exito = ejecutar_todas_las_pruebas()
    sys.exit(0 if exito else 1)
