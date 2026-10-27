"""
===============================================================================
PANEL DE CONTROL WEB Y SERVIDOR CLOUD 24/7 — TAPMEALS (@tapmeals.yopal)
===============================================================================
Servidor Flask con API REST, Editor de Reglas Dinámicas y Dashboard 24/7:
- Monitoreo en tiempo real del estado del bot (24/7)
- Editor Dinámico de Reglas por Palabras Clave (Precios, Domicilios, Macros, etc.)
- Simulador de chat en vivo con diagnóstico de regla disparada
- Registro de actividad e interacciones de clientes
- Endpoints de Webhook oficial para Meta / Instagram Graph API
- Guía y configuración de despliegue en la nube (Render / ManyChat oficial)
===============================================================================
"""

import os
import sys
import time
import json
import re
import unicodedata
import threading
import webbrowser
import random
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

# Configurar salida UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path(r"C:\Users\MSI\.gemini\antigravity\scratch\tapmeals_project")
KIT_DIR = Path(r"C:\Users\MSI\Downloads\TapMeals_Kit_Editable_ApoloStyle")

CONFIG_FILE = BASE_DIR / "config.json"
HISTORY_FILE = BASE_DIR / "taptap_processed_history.json"
if not HISTORY_FILE.exists() and (PROJECT_DIR / "taptap_processed_history.json").exists():
    HISTORY_FILE = PROJECT_DIR / "taptap_processed_history.json"

DEFAULT_MENU_IMAGE = BASE_DIR / "Menu_Oficial_TapMeals_Yopal.png"
if not DEFAULT_MENU_IMAGE.exists():
    DEFAULT_MENU_IMAGE = KIT_DIR / "Menu_Oficial_TapMeals_Yopal.png"

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# Estado en memoria
server_start_time = time.time()
bot_logs = []
bot_worker_thread = None
bot_running_flag = False

DEFAULT_RULES = [
    {
        "id": "rule_taptap",
        "name": "Menú Oficial TapTap",
        "keywords": ["taptap", "tap tap", "tap-tap", "tapp", "menu", "carta"],
        "match_type": "contains",
        "channels": ["dm", "solicitud", "comentario"],
        "reply_text": "¡Hola atleta! 🍱⚡ Aquí tienes el menú oficial de TapMeals en Yopal.\n\n💡 Cero fritos ni aceites quemados. Cada bandeja viene pesada en báscula digital con etiqueta sellada en la tapa.",
        "comment_reply": "¡Te acabamos de enviar el menú oficial por mensaje directo! Revisa tu DM 🍱⚡",
        "send_image": True,
        "enabled": True
    },
    {
        "id": "rule_precios",
        "name": "Precios y Opciones",
        "keywords": ["precio", "precios", "cuanto vale", "costo", "valor", "cuanto cuesta", "tarifa", "tarifas"],
        "match_type": "contains",
        "channels": ["dm", "solicitud"],
        "reply_text": "¡Hola! 🍱⚡ Nuestros precios oficiales en Yopal son:\n\n1. Pechuga a la Plancha Fit (150g proteína magra): $13.500 COP\n2. Ternera Magra Llanera (140g proteína magra): $14.500 COP\n3. Bowl Doble Proteína (200g pollo + huevo cocido): $15.000 COP\n\nTodos incluyen porción de carbohidrato limpio medido al gramo y vegetales frescos.",
        "comment_reply": "¡Precios enviados al DM! Revisa tu bandeja de entrada 🍱⚡",
        "send_image": True,
        "enabled": True
    },
    {
        "id": "rule_saludo",
        "name": "Saludo e Información General",
        "keywords": ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "info", "informacion", "almuerzo", "almuerzos", "comida", "fitness", "saludos"],
        "match_type": "contains",
        "channels": ["dm", "solicitud"],
        "reply_text": "¡Hola atleta! 🍱⚡ Bienvenido a TapMeals Yopal.\n\nPreparamos almuerzos fitness con macros certificados, proteína magra pesada en báscula digital y carbohidratos limpios. Cero aceites quemados.\n\nPuedes escribir 'Precio' para ver los costos o 'TapTap' para recibir la carta completa con fotos. ¿Qué plato te gustaría ordenar hoy?",
        "comment_reply": "¡Hola atleta! Te enviamos toda la información por mensaje directo 🍱⚡",
        "send_image": True,
        "enabled": True
    },
    {
        "id": "rule_gracias",
        "name": "Agradecimiento y Cierre",
        "keywords": ["gracias", "muchas gracias", "vale", "ok", "listo", "de una", "genial", "perfecto"],
        "match_type": "contains",
        "channels": ["dm", "solicitud"],
        "reply_text": "¡Con el mayor gusto, atleta! 🍱⚡ En TapMeals estamos para potenciar tu rendimiento con comida limpia pesada en báscula digital.\n\nSi deseas agendar tu almuerzo de hoy, escribe 'Pedido' o contáctanos a WhatsApp para apartar tu porción. ¡A darle con toda!",
        "comment_reply": "¡Con el mayor gusto atleta! A la orden en TapMeals 🍱⚡",
        "send_image": False,
        "enabled": True
    },
    {
        "id": "rule_domicilios",
        "name": "Horarios y Zonas de Entrega",
        "keywords": ["domicilio", "domicilios", "donde entregan", "cobertura", "horario", "a que hora", "entrega", "despacho"],
        "match_type": "contains",
        "channels": ["dm", "solicitud"],
        "reply_text": "📍 Cobertura: Todo el casco urbano de Yopal (gimnasios, oficinas y residencias).\n\n⏰ Horario de pedidos: 07:00 AM a 10:30 AM.\n🚀 Despachos calientes: Entre 11:30 AM y 01:00 PM listos para comer.",
        "comment_reply": "¡Información de domicilios enviada por interno! Revisa tu DM 📍",
        "send_image": False,
        "enabled": True
    },
    {
        "id": "rule_macros",
        "name": "Macros y Báscula Digital",
        "keywords": ["macros", "proteina", "calorias", "gramos", "gramera", "peso", "deficit", "volumen", "nutricion", "calculadora", "calcular", "cuanta proteina"],
        "match_type": "contains",
        "channels": ["dm", "solicitud", "comentario"],
        "reply_text": "⚡ En TapMeals no adivinamos: cada bandeja viene pesada en báscula digital con 150g de pechuga limpia (38g proteína magra) certificados en la tapa.\n\n📊 Puedes calcular tus gramos diarios exactos según tu peso y meta en nuestra Calculadora Web gratuita:\n👉 https://tapmeals-panel-cloud.onrender.com/macros\n\n¿Quieres apartar tu cupo en la degustación piloto de Yopal?",
        "comment_reply": "¡Calculadora de macros y detalles de proteína enviados a tu DM! 📊⚡",
        "send_image": False,
        "enabled": True
    },
    {
        "id": "rule_pedido",
        "name": "Hacer Pedido / WhatsApp Directo",
        "keywords": ["pedir", "pedido", "quiero pedir", "comprar", "ordenar", "whatsapp", "agendar", "quiero un almuerzo"],
        "match_type": "contains",
        "channels": ["dm", "solicitud"],
        "reply_text": "¡Excelente elección, atleta! 📲⚡ Puedes agendar tu pedido en 30 segundos directamente en nuestro WhatsApp oficial con el plato que deseas:\n\n👉 https://api.whatsapp.com/send?phone=573100000000&text=Hola%20TapMeals!%20Quiero%20agendar%20mi%20almuerzo%20fitness%20de%20hoy%20🍱",
        "comment_reply": "¡Link directo de WhatsApp enviado a tu DM para tomar tu pedido! 📲",
        "send_image": False,
        "enabled": True
    },
    {
        "id": "rule_gym",
        "name": "Convenio Gimnasios Yopal",
        "keywords": ["gym", "gimnasio", "smartfit", "bodytech", "convenio", "descuento", "atleta", "entreno"],
        "match_type": "contains",
        "channels": ["dm", "solicitud", "comentario"],
        "reply_text": "🏋️‍♂️ ¿Entrenas en SmartFit, Bodytech o algún box de Yopal? Tienes $2.000 COP de descuento en tu primer almuerzo mostrando tu membresía activa al repartidor.\n\nEscribe 'TapTap' para ver la carta completa.",
        "comment_reply": "¡Beneficio de gimnasio enviado a tu DM! Revisa tu bandeja 🏋️‍♂️⚡",
        "send_image": False,
        "enabled": True
    }
]


def log_event(tipo: str, remitente: str, detalle: str, canal: str = "DM"):
    """Registra un evento visual para el dashboard."""
    evento = {
        "id": int(time.time() * 1000),
        "timestamp": time.strftime("%H:%M:%S"),
        "tipo": tipo,       # 'exito', 'solicitud', 'comentario', 'aviso', 'error'
        "remitente": remitente,
        "detalle": detalle,
        "canal": canal
    }
    bot_logs.insert(0, evento)
    if len(bot_logs) > 300:
        bot_logs.pop()


def normalizar_texto(texto: str) -> str:
    """Elimina tildes, signos y convierte a minúsculas para análisis robusto."""
    if not texto:
        return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()


def verificar_taptap(texto: str) -> bool:
    """Detecta 'TapTap' en cualquier formato (mayúsculas, minúsculas, espacios, símbolos)."""
    if not texto or not isinstance(texto, str):
        return False
    norm = normalizar_texto(texto)
    if re.search(r'tap+[\s\-_.,!¡?¿]*tap+', norm):
        return True
    solo_letras = re.sub(r'[^a-z]', '', norm)
    if 'taptap' in solo_letras:
        return True
    return False


def es_solicitud_menu(texto: str) -> bool:
    """Detecta si el mensaje es TapTap o una solicitud explícita de la carta/menú/precios."""
    if not texto or not isinstance(texto, str):
        return False
    limpio = texto.strip()
    if not limpio:
        return False
    if verificar_taptap(limpio):
        return True
    norm = normalizar_texto(limpio)
    palabras_clave = [
        'menu', 'carta', 'precio', 'precios', 'costo', 'costos', 'info',
        'informacion', 'hola', 'buenas', 'buenos dias', 'buenas tardes',
        'pedido', 'pedir', 'comida', 'almuerzo', 'fit', 'proteina', 'domicilio', 'taptap'
    ]
    return any(p in norm for p in palabras_clave)


def evaluar_reglas(texto: str, canal: str, conf: dict) -> dict:
    """
    Evalúa el mensaje entrante contra el motor dinámico de reglas.
    Retorna la regla coincidente, la respuesta, canal y adjunto de imagen.
    """
    if not texto or not isinstance(texto, str):
        return {"triggers": False, "reason": "Mensaje vacío o no textual", "rule": None}
    
    texto_limpio = texto.strip()
    if not texto_limpio:
        return {"triggers": False, "reason": "Mensaje vacío", "rule": None}
    
    norm = normalizar_texto(texto_limpio)
    tokens = set(re.findall(r'\b\w+\b', norm))
    
    rules = conf.get("rules", DEFAULT_RULES)
    
    for rule in rules:
        if not rule.get("enabled", True):
            continue
            
        r_channels = rule.get("channels", ["dm"])
        if isinstance(r_channels, str):
            r_channels = [r_channels]
            
        # Verificar si el canal coincide
        channel_matches = False
        if "both" in r_channels:
            channel_matches = True
        elif canal in r_channels:
            channel_matches = True
        elif canal == "solicitud" and ("dm" in r_channels or "both" in r_channels):
            channel_matches = True
            
        if not channel_matches:
            continue
            
        match_type = rule.get("match_type", "contains")
        keywords = [normalizar_texto(k) for k in rule.get("keywords", []) if k.strip()]
        
        # Caso especial para TapTap
        if rule.get("id") == "rule_taptap" or any("taptap" in k for k in keywords):
            if verificar_taptap(texto_limpio):
                return {
                    "triggers": True,
                    "rule": rule,
                    "matched_kw": "TapTap",
                    "reason": f"Disparado por regla '{rule.get('name')}' (coincidencia de TapTap)",
                    "dm_response": rule.get("reply_text") or conf.get("welcome_message"),
                    "comment_reply": rule.get("comment_reply") or conf.get("comment_public_reply"),
                    "has_image": rule.get("send_image", True),
                    "image_url": "/menu-image"
                }
                
        # Matching normal de palabras clave
        for kw in keywords:
            matched = False
            if match_type == "exact":
                if norm == kw:
                    matched = True
            elif match_type == "starts_with":
                if norm.startswith(kw):
                    matched = True
            else: # contains
                if " " in kw:
                    if kw in norm:
                        matched = True
                else:
                    if kw in tokens or any(kw in t for t in tokens):
                        matched = True
                        
            if matched:
                return {
                    "triggers": True,
                    "rule": rule,
                    "matched_kw": kw,
                    "reason": f"Disparado por regla '{rule.get('name')}' (palabra clave detectada: '{kw}')",
                    "dm_response": rule.get("reply_text") or conf.get("welcome_message"),
                    "comment_reply": rule.get("comment_reply") or conf.get("comment_public_reply"),
                    "has_image": rule.get("send_image", False),
                    "image_url": "/menu-image" if rule.get("send_image", False) else None
                }
                
    # Fallback si no hubo regla personalizada pero coincide con TapTap o menú genérico
    if verificar_taptap(texto_limpio):
        return {
            "triggers": True,
            "rule": None,
            "matched_kw": "TapTap",
            "reason": "Detectó 'TapTap' de forma ultra flexible (regla base)",
            "dm_response": conf.get("welcome_message"),
            "comment_reply": conf.get("comment_public_reply"),
            "has_image": True,
            "image_url": "/menu-image"
        }
        
    if canal in ["dm", "solicitud"]:
        return {
            "triggers": True,
            "rule": None,
            "matched_kw": "asistente_general",
            "reason": "Respuesta asistida para nuevo contacto por mensaje directo",
            "dm_response": (
                "¡Hola atleta! 🍱⚡ Bienvenido a TapMeals en Yopal.\n\n"
                "Para ayudarte con tu almuerzo fitness de inmediato, cuéntanos qué necesitas o escribe una de estas palabras clave:\n"
                "• *Precio*: Lista y valores de nuestros 3 platos.\n"
                "• *TapTap* o *Menú*: Para ver la carta completa con fotos y gramajes.\n"
                "• *Domicilio*: Cobertura y horarios de entrega.\n"
                "• *Pedido*: Enlace directo de WhatsApp para agendar tu entrega."
            ),
            "comment_reply": None,
            "has_image": True,
            "image_url": "/menu-image"
        }

    return {
        "triggers": False,
        "rule": None,
        "matched_kw": None,
        "reason": f"El comentario no coincide con ninguna de las {len(rules)} reglas activas para comentarios",
        "dm_response": None,
        "comment_reply": None,
        "has_image": False,
        "image_url": None
    }


def cargar_config() -> dict:
    default_config = {
        "bot_enabled": True,
        "trigger_keyword": "TapTap",
        "welcome_message": "¡Hola atleta! 🍱⚡ Aquí tienes el menú oficial de TapMeals en Yopal.\n\n💡 Cero fritos ni aceites quemados. Cada bandeja viene pesada en báscula digital con etiqueta sellada en la tapa.",
        "comment_public_reply": "¡Te acabamos de enviar el menú oficial por mensaje directo! Revisa tu DM 🍱⚡",
        "closed_dms_reply": "Tu cuenta tiene bloqueados los DMs de externos 🔒 Porfa envíanos tú un mensaje al directo con la palabra 'TapTap' y te llegará la carta de una 🍱⚡",
        "cooldown_seconds": 45,
        "scan_interval_seconds": 1.5,
        "menu_image_path": "Menu_Oficial_TapMeals_Yopal.png",
        "cloud_mode": "manychat_recommended",
        "rules": DEFAULT_RULES
    }
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            default_config.update(saved)
            if not default_config.get("rules"):
                default_config["rules"] = DEFAULT_RULES
        except Exception:
            pass
    return default_config


def guardar_config(conf: dict):
    CONFIG_FILE.write_text(json.dumps(conf, indent=2, ensure_ascii=False), encoding="utf-8")


def cargar_historial() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"comentarios": [], "dms": [], "known_threads": []}


def guardar_historial(historial: dict):
    try:
        historial["comentarios"] = historial.get("comentarios", [])[-2000:]
        historial["dms"] = historial.get("dms", [])[-2000:]
        historial["known_threads"] = historial.get("known_threads", [])[-50:]
        HISTORY_FILE.write_text(json.dumps(historial, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[Aviso] No se pudo guardar historial: {e}")


def bucle_trabajador_instagram(session_file: Path):
    """
    Bucle en segundo plano de ultra-resistencia para responder automáticamente en Instagram:
    - Message Requests / Solicitudes de mensajes de nuevos usuarios (direct_pending_inbox)
    - DMs en threads conocidos y nuevos (direct_thread / direct_threads con Circuit Breaker)
    - Comentarios en publicaciones y reels (media_comments)
    - Delays humanos aleatorios de 3 a 5 seg para proteger la cuenta contra bloqueos
    """
    global bot_running_flag
    try:
        from instagrapi import Client
    except ImportError:
        log_event("aviso", "Sistema", "instagrapi no instalado, bot local en pausa.", "Sistema")
        return

    cl = Client()
    cl.delay_range = [0.3, 0.6]

    try:
        cl.load_settings(session_file)
        account = cl.account_info()
        my_user_id = str(account.pk)
        log_event("exito", f"@{account.username}", "Sesión de Instagram verificada y conectada.", "Instagram")
        print(f"[TapMeals Bot] Sesión activa como @{account.username} (pk={my_user_id})")
    except Exception as e:
        log_event("aviso", "Instagram", f"Error validando sesión: {e}", "Instagram")
        print(f"[TapMeals Bot] Error cargando sesión: {e}")
        return

    VERIFIED_KNOWN_THREADS = [
        "340282366841710301244259259610874989555",  # @julian.monroy10 (Julian Monroy)
        "340282366841710301244259647975719645042",  # @alitos0246 (Alexander Monroy)
        "340282366841710301244259609051612611551",  # @juanf_elipemendoza (Juan Felipe Mendoza)
        "340282366841710301244259324659438433812",  # @tomassalazarrodriguez
        "340282366841710301244259265388784045112",  # @juan_garcia.64
        "340282366841710301244260000604202212981",  # @lucecita_2
        "340282366841710301244260346857080832537",  # @juanjose_vacagz
        "340282366841710301244259626122790867835",  # @danielmatiasprieto1
        "340282366841710301244260143586137853579",  # @gg8866760
    ]

    historial = cargar_historial()
    dms_procesados = set(historial.get("dms", []))
    comentarios_procesados = set(historial.get("comentarios", []))
    known_threads = set(historial.get("known_threads", []))
    for vt in VERIFIED_KNOWN_THREADS:
        known_threads.add(vt)

    circuit_breaker_until = 0
    cached_medias = []
    ultimo_refresh_medias = 0
    cooldown_threads = {}
    cooldown_seg = 6

    ciclo = 0
    while bot_running_flag:
        try:
            ciclo += 1
            conf = cargar_config()
            if not conf.get("bot_enabled", True):
                time.sleep(2)
                continue

            ahora = time.time()

            # -------------------------------------------------------------
            # 1. COMENTARIOS EN REELS Y POSTS (En CADA ciclo para respuesta ultrarrápida < 2s)
            # -------------------------------------------------------------
            if ahora - ultimo_refresh_medias > 45 or not cached_medias:
                try:
                    all_m = []
                    # Obtener últimos posts del feed
                    try:
                        m_feed = cl.user_medias(cl.user_id, amount=3)
                        all_m.extend([m.pk for m in m_feed])
                    except Exception:
                        pass
                    # Obtener últimos reels / clips
                    try:
                        m_clips = cl.user_clips(cl.user_id, amount=3)
                        all_m.extend([clip.pk for clip in m_clips])
                    except Exception:
                        pass
                    # Guardar únicos manteniendo orden reciente
                    seen_pk = set()
                    cached_medias = []
                    for mpk in all_m:
                        if mpk not in seen_pk:
                            seen_pk.add(mpk)
                            cached_medias.append(mpk)
                    ultimo_refresh_medias = ahora
                except Exception:
                    pass

            for media_pk in cached_medias:
                try:
                    comments = cl.media_comments(media_pk, amount=6)
                    for c in comments:
                        cid = str(c.pk)
                        if cid in comentarios_procesados or str(c.user.pk) == my_user_id:
                            continue

                        eval_res = evaluar_reglas(c.text, "comentario", conf)
                        if eval_res.get("triggers"):
                            username = c.user.username
                            user_pk = c.user.pk
                            regla = eval_res.get("rule")
                            nombre_regla = regla["name"] if regla else "Regla Comentario"
                            log_event("comentario", f"@{username}", f"Comentario: \"{c.text}\" -> {nombre_regla}", "Comentario")
                            print(f"\n[⚡ COMENTARIO EN REEL/POST] @{username}: \"{c.text}\" -> {nombre_regla}")

                            comentarios_procesados.add(cid)
                            historial.setdefault("comentarios", []).append(cid)
                            guardar_historial(historial)

                            # A) Enviar DM con información y foto del menú de inmediato
                            dm_ok = False
                            try:
                                reply = eval_res.get("dm_response") or conf.get("welcome_message")
                                cl.direct_send(reply, user_ids=[int(user_pk)])
                                dm_ok = True
                                if eval_res.get("has_image") and DEFAULT_MENU_IMAGE.exists():
                                    time.sleep(0.6)
                                    try:
                                        cl.direct_send_photo(DEFAULT_MENU_IMAGE, user_ids=[int(user_pk)])
                                    except Exception:
                                        pass
                            except Exception:
                                dm_ok = False

                            # B) Publicar respuesta oficial en el Reel / Post (con fallback robusto)
                            try:
                                if dm_ok:
                                    pub = eval_res.get("comment_reply") or conf.get("comment_public_reply")
                                    resp = f"@{username} {pub}"
                                else:
                                    resp = f"@{username} {conf.get('closed_dms_reply')}"

                                try:
                                    cl.media_comment(media_pk, resp, replied_to_comment_id=c.pk)
                                except Exception:
                                    # Fallback directo al reel si falla respuesta anidada
                                    try:
                                        cl.media_comment(media_pk, resp)
                                    except Exception as e_pub:
                                        print(f"[Aviso] No se pudo comentar reel: {e_pub}")
                            except Exception as e_comm_resp:
                                print(f"[Error comentario público] {e_comm_resp}")

                            # C) Registrar nuevo hilo en known_threads para monitoreo instantáneo
                            try:
                                res_th = cl.private_request(f"direct_v2/threads/get_by_participants/?recipient_users=[{user_pk}]")
                                t_id_new = res_th.get("thread", {}).get("thread_id")
                                if t_id_new and str(t_id_new) not in known_threads:
                                    known_threads.add(str(t_id_new))
                            except Exception:
                                pass
                except Exception:
                    pass

            # -------------------------------------------------------------
            # 2. SOLICITUDES DE MENSAJE (Nuevos atletas que escriben por primera vez)
            # -------------------------------------------------------------
            try:
                pending = cl.direct_pending_inbox(amount=4)
                for thread in pending:
                    t_id = str(thread.id)
                    known_threads.add(t_id)

                    user = thread.users[0] if thread.users else None
                    username = user.username if user else "usuario"

                    msgs = thread.messages if thread.messages else []
                    if not msgs:
                        continue
                    m = msgs[0]
                    m_id = str(m.id)
                    if m_id in dms_procesados or str(m.user_id) == my_user_id:
                        continue

                    eval_res = evaluar_reglas(m.text, "solicitud", conf)
                    if eval_res.get("triggers"):
                        regla = eval_res.get("rule")
                        nombre_regla = regla["name"] if regla else "Asistente TapTap"
                        log_event("solicitud", f"@{username}", f"Solicitud: \"{m.text}\" -> {nombre_regla}", "Solicitud")
                        print(f"\n[⚡ SOLICITUD RESPONDIDA] @{username}: \"{m.text}\" -> {nombre_regla}")

                        dms_procesados.add(m_id)
                        historial.setdefault("dms", []).append(m_id)
                        guardar_historial(historial)

                        try:
                            cl.direct_pending_approve(thread.id)
                        except Exception:
                            pass

                        reply = eval_res.get("dm_response") or conf.get("welcome_message")
                        cl.direct_send(reply, thread_ids=[thread.id])

                        if eval_res.get("has_image") and DEFAULT_MENU_IMAGE.exists():
                            time.sleep(0.6)
                            try:
                                cl.direct_send_photo(DEFAULT_MENU_IMAGE, thread_ids=[thread.id])
                            except Exception:
                                pass
            except Exception:
                pass

            # -------------------------------------------------------------
            # 3. THREADS ACTIVOS CONOCIDOS (Round-Robin ultra-rápido de 2 por ciclo)
            # -------------------------------------------------------------
            known_list = list(known_threads)
            if known_list:
                batch_size = 2
                idx_start = (ciclo * batch_size) % len(known_list)
                current_batch = [known_list[(idx_start + i) % len(known_list)] for i in range(min(batch_size, len(known_list)))]
                for t_id in current_batch:
                    try:
                        thread_data = cl.direct_thread(t_id)
                        msgs = thread_data.messages if hasattr(thread_data, 'messages') else []
                        if not msgs:
                            continue

                        # Extraer mensajes entrantes que no sean nuestros y no estén procesados
                        nuevos = []
                        for m in msgs[:6]:
                            if str(m.user_id) == my_user_id:
                                break
                            mid = str(m.id)
                            if mid not in dms_procesados and m.text:
                                nuevos.append(m)

                        if not nuevos:
                            continue

                        sender_user = thread_data.users[0] if getattr(thread_data, 'users', None) else None
                        username = sender_user.username if sender_user else "atleta"

                        for m in reversed(nuevos):
                            mid = str(m.id)
                            eval_res = evaluar_reglas(m.text, "dm", conf)
                            if eval_res.get("triggers"):
                                regla = eval_res.get("rule")
                                nombre_regla = regla["name"] if regla else "Asistente DM"
                                log_event("exito", f"@{username}", f"DM: \"{m.text}\" -> {nombre_regla}", "DM")
                                print(f"\n[⚡ DM RESPONDIDO] @{username}: \"{m.text}\" -> {nombre_regla}")

                                dms_procesados.add(mid)
                                historial.setdefault("dms", []).append(mid)
                                guardar_historial(historial)

                                reply = eval_res.get("dm_response") or conf.get("welcome_message")
                                cl.direct_send(reply, thread_ids=[thread_data.id])

                                if eval_res.get("has_image") and DEFAULT_MENU_IMAGE.exists():
                                    time.sleep(0.6)
                                    try:
                                        cl.direct_send_photo(DEFAULT_MENU_IMAGE, thread_ids=[thread_data.id])
                                    except Exception:
                                        pass
                            else:
                                dms_procesados.add(mid)
                                historial.setdefault("dms", []).append(mid)
                                guardar_historial(historial)
                    except Exception:
                        pass

            # -------------------------------------------------------------
            # 4. DIRECT THREADS INBOX (Con Circuit Breaker anti-403)
            # -------------------------------------------------------------
            if ahora > circuit_breaker_until:
                try:
                    threads = cl.direct_threads(amount=2)
                    for thread in threads:
                        t_id = str(thread.id)
                        known_threads.add(t_id)
                        if ahora - cooldown_threads.get(t_id, 0) < cooldown_seg:
                            continue

                        msgs = thread.messages[:2] if thread.messages else []
                        for m in msgs:
                            mid = str(m.id)
                            if mid in dms_procesados or str(m.user_id) == my_user_id:
                                continue

                            eval_res = evaluar_reglas(m.text, "dm", conf)
                            if eval_res.get("triggers"):
                                user = thread.users[0] if thread.users else None
                                username = user.username if user else "atleta"
                                regla = eval_res.get("rule")
                                nombre_regla = regla["name"] if regla else "Regla DM"
                                log_event("exito", f"@{username}", f"DM: \"{m.text}\" -> {nombre_regla}", "DM")
                                print(f"\n[⚡ DM INBOX RESPONDIDO] @{username}: \"{m.text}\" -> {nombre_regla}")

                                dms_procesados.add(mid)
                                historial.setdefault("dms", []).append(mid)
                                guardar_historial(historial)
                                cooldown_threads[t_id] = ahora

                                reply = eval_res.get("dm_response") or conf.get("welcome_message")
                                cl.direct_send(reply, thread_ids=[thread.id])

                                if eval_res.get("has_image") and DEFAULT_MENU_IMAGE.exists():
                                    time.sleep(0.6)
                                    try:
                                        cl.direct_send_photo(DEFAULT_MENU_IMAGE, thread_ids=[thread.id])
                                    except Exception:
                                        pass
                except Exception as e_th:
                    if "403" in str(e_th) or "item_ack" in str(e_th):
                        circuit_breaker_until = ahora + 600
                        log_event("aviso", "Circuit Breaker", "Inbox en cooldown (403). Conmutando a modo Directo & Solicitudes.", "Instagram")

            # Descubrimiento periódico de nuevos hilos de seguidores (cada 60 ciclos)
            if ciclo > 1 and ciclo % 60 == 0:
                try:
                    flw = cl.user_followers(cl.user_id, amount=20)
                    for uid in list(flw.keys()):
                        try:
                            res_p = cl.private_request(f"direct_v2/threads/get_by_participants/?recipient_users=[{uid}]")
                            th_p = res_p.get("thread", {})
                            tid_p = th_p.get("thread_id")
                            if tid_p and str(tid_p) not in known_threads:
                                known_threads.add(str(tid_p))
                                log_event("aviso", "Descubridor", f"Nuevo hilo de @{flw[uid].username} registrado: {tid_p}", "Sistema")
                        except Exception:
                            pass
                except Exception:
                    pass

            historial["known_threads"] = list(known_threads)[-50:]
            guardar_historial(historial)

            # Pausa suave ultrarrápida (1.2 a 1.8 segundos)
            time.sleep(random.uniform(1.2, 1.8))

        except Exception as e_main:
            time.sleep(2)


def iniciar_hilo_bot_si_es_posible():
    global bot_worker_thread, bot_running_flag
    if bot_worker_thread is not None and bot_worker_thread.is_alive():
        return
    session_file = BASE_DIR / "tapmeals_ig_session.json"
    if not session_file.exists():
        session_file = PROJECT_DIR / "tapmeals_ig_session.json"
    if not session_file.exists():
        session_file = Path(r"C:\Users\MSI\tapmeals_ig_session.json")
    if session_file.exists():
        bot_running_flag = True
        bot_worker_thread = threading.Thread(target=bucle_trabajador_instagram, args=(session_file,), daemon=True)
        bot_worker_thread.start()
        log_event("exito", "Bot Instagram", "Motor automático iniciado en segundo plano.", "Instagram")
        print(f"[TapMeals Bot] Hilo trabajador de Instagram iniciado con sesión: {session_file.name}")


# Lanzar automáticamente al cargar el servidor
iniciar_hilo_bot_si_es_posible()



# -----------------------------------------------------------------------------
# RUTAS DE LA INTERFAZ WEB (FRONTEND)
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/macros')
@app.route('/calculadora')
def macros_calculator():
    return render_template("macros.html")


@app.route('/menu-image')
def get_menu_image():
    conf = cargar_config()
    p_str = conf.get("menu_image_path", "Menu_Oficial_TapMeals_Yopal.png")
    p = Path(p_str)
    if not p.is_absolute():
        p = BASE_DIR / p_str
    if p.exists():
        return send_file(p, mimetype='image/png')
    if DEFAULT_MENU_IMAGE.exists():
        return send_file(DEFAULT_MENU_IMAGE, mimetype='image/png')
    return "Imagen no encontrada", 404


# -----------------------------------------------------------------------------
# RUTAS DE LA API REST (BACKEND)
# -----------------------------------------------------------------------------

@app.route('/api/status', methods=['GET'])
def get_status():
    conf = cargar_config()
    hist = cargar_historial()
    uptime_sec = int(time.time() - server_start_time)
    horas = uptime_sec // 3600
    minutos = (uptime_sec % 3600) // 60
    segundos = uptime_sec % 60
    
    return jsonify({
        "status": "online",
        "bot_enabled": conf.get("bot_enabled", True),
        "uptime": f"{horas:02d}h {minutos:02d}m {segundos:02d}s",
        "total_comentarios": len(hist.get("comentarios", [])),
        "total_dms": len(hist.get("dms", [])),
        "trigger_keyword": conf.get("trigger_keyword", "TapTap"),
        "total_rules": len(conf.get("rules", [])),
        "active_rules": len([r for r in conf.get("rules", []) if r.get("enabled", True)]),
        "logs_count": len(bot_logs),
        "cloud_mode": conf.get("cloud_mode", "manychat_recommended"),
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route('/api/toggle-bot', methods=['POST'])
def toggle_bot():
    global bot_running_flag
    conf = cargar_config()
    nuevo_estado = not conf.get("bot_enabled", True)
    conf["bot_enabled"] = nuevo_estado
    guardar_config(conf)
    if nuevo_estado:
        iniciar_hilo_bot_si_es_posible()
    else:
        bot_running_flag = False
    estado_str = "ACTIVADO" if nuevo_estado else "PAUSADO"
    log_event("aviso", "Sistema", f"El contestador automático fue {estado_str} desde el panel web.", "Control")
    return jsonify({"success": True, "bot_enabled": nuevo_estado})


@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(cargar_config())


@app.route('/api/config', methods=['POST'])
def update_config():
    try:
        data = request.json or {}
        conf = cargar_config()
        for key in ["welcome_message", "comment_public_reply", "closed_dms_reply", "cooldown_seconds", "scan_interval_seconds", "trigger_keyword"]:
            if key in data:
                conf[key] = data[key]
        guardar_config(conf)
        log_event("exito", "Configuración", "Ajustes globales de mensajes actualizados.", "Ajustes")
        return jsonify({"success": True, "config": conf})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# -----------------------------------------------------------------------------
# CRUD DEL MOTOR DE REGLAS DE PALABRAS CLAVE
# -----------------------------------------------------------------------------

@app.route('/api/rules', methods=['GET'])
def get_rules():
    conf = cargar_config()
    return jsonify({"success": True, "rules": conf.get("rules", DEFAULT_RULES)})


@app.route('/api/rules', methods=['POST'])
def create_or_update_rule():
    try:
        data = request.json or {}
        conf = cargar_config()
        rules = conf.get("rules", [])
        
        rule_id = data.get("id")
        if not rule_id:
            rule_id = f"rule_{int(time.time() * 1000)}"
            data["id"] = rule_id
            
        if "enabled" not in data:
            data["enabled"] = True
        if "send_image" not in data:
            data["send_image"] = False
            
        # Parse keywords list
        raw_kw = data.get("keywords", [])
        if isinstance(raw_kw, str):
            data["keywords"] = [k.strip() for k in raw_kw.split(",") if k.strip()]
        else:
            data["keywords"] = [str(k).strip() for k in raw_kw if str(k).strip()]
            
        # Parse channels
        raw_ch = data.get("channels", ["dm"])
        if isinstance(raw_ch, str):
            data["channels"] = [c.strip() for c in raw_ch.split(",") if c.strip()]
            
        existing_idx = next((i for i, r in enumerate(rules) if r.get("id") == rule_id), None)
        if existing_idx is not None:
            rules[existing_idx] = data
            accion = "actualizada"
        else:
            rules.append(data)
            accion = "creada"
            
        conf["rules"] = rules
        guardar_config(conf)
        
        log_event("exito", "Reglas", f"Regla '{data.get('name', rule_id)}' {accion} exitosamente.", "Editor")
        return jsonify({"success": True, "rule": data, "rules": rules})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/rules/<rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    conf = cargar_config()
    rules = conf.get("rules", [])
    nuevas = [r for r in rules if r.get("id") != rule_id]
    if len(nuevas) == len(rules):
        return jsonify({"success": False, "error": "Regla no encontrada"}), 404
        
    conf["rules"] = nuevas
    guardar_config(conf)
    log_event("aviso", "Reglas", f"Regla con ID '{rule_id}' eliminada.", "Editor")
    return jsonify({"success": True, "rules": nuevas})


@app.route('/api/rules/<rule_id>/toggle', methods=['POST'])
def toggle_rule(rule_id):
    conf = cargar_config()
    rules = conf.get("rules", [])
    for r in rules:
        if r.get("id") == rule_id:
            r["enabled"] = not r.get("enabled", True)
            guardar_config(conf)
            estado = "activada" if r["enabled"] else "pausada"
            log_event("aviso", "Reglas", f"Regla '{r.get('name')}' {estado}.", "Editor")
            return jsonify({"success": True, "enabled": r["enabled"], "rules": rules})
    return jsonify({"success": False, "error": "Regla no encontrada"}), 404


@app.route('/api/rules/reset-defaults', methods=['POST'])
def reset_rules_to_defaults():
    conf = cargar_config()
    conf["rules"] = DEFAULT_RULES
    guardar_config(conf)
    log_event("exito", "Reglas", "Reglas restauradas a los 6 valores predeterminados fitness.", "Editor")
    return jsonify({"success": True, "rules": DEFAULT_RULES})


@app.route('/api/upload-menu', methods=['POST'])
def upload_menu():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No se envió ningún archivo"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "Nombre de archivo vacío"}), 400
    
    filename = secure_filename(file.filename)
    dest_path = BASE_DIR / "Menu_Oficial_TapMeals_Yopal.png"
    file.save(dest_path)
    
    conf = cargar_config()
    conf["menu_image_path"] = "Menu_Oficial_TapMeals_Yopal.png"
    guardar_config(conf)
    
    log_event("exito", "Menú", "Nueva imagen del menú oficial 4:5 subida y actualizada.", "Carta")
    return jsonify({"success": True, "path": str(dest_path)})


@app.route('/api/test-simulator', methods=['POST'])
@app.route('/api/rules/test-simulate', methods=['POST'])
def test_simulator():
    """Simula en tiempo real la respuesta exacta del bot para cualquier mensaje."""
    data = request.json or {}
    texto = data.get("text", "")
    tipo_canal = data.get("channel", "dm") # 'dm', 'solicitud', 'comentario'
    
    conf = cargar_config()
    res = evaluar_reglas(texto, tipo_canal, conf)
    
    if res["triggers"]:
        rule_name = res["rule"]["name"] if res.get("rule") else "Regla Base TapTap"
        rule_id = res["rule"]["id"] if res.get("rule") else "base"
        log_event("exito", "@atleta_simulado", f"Simulación {tipo_canal.upper()}: \"{texto}\" -> Disparó '{rule_name}'", "Simulador")
        return jsonify({
            "triggers": True,
            "rule_id": rule_id,
            "rule_name": rule_name,
            "matched_kw": res.get("matched_kw"),
            "reason": res["reason"],
            "dm_response": res["dm_response"],
            "public_comment_reply": f"@atleta_simulado {res['comment_reply']}" if res.get("comment_reply") else None,
            "has_image": res["has_image"],
            "image_url": res["image_url"],
            "approved_request": (tipo_canal == "solicitud")
        })
    else:
        return jsonify({
            "triggers": False,
            "rule_name": None,
            "rule_id": None,
            "matched_kw": None,
            "reason": res["reason"],
            "dm_response": None,
            "public_comment_reply": None,
            "has_image": False
        })


@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify({"logs": bot_logs})


@app.route('/api/clear-logs', methods=['POST'])
def clear_logs():
    global bot_logs
    bot_logs = []
    return jsonify({"success": True})


# -----------------------------------------------------------------------------
# WEBHOOK OFICIAL DE META GRAPH API (INSTAGRAM CLOUD)
# -----------------------------------------------------------------------------

@app.route('/webhook', methods=['GET'])
def meta_webhook_verification():
    """Verificación de Webhook oficial de Meta / Instagram Graph API."""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN", "tapmeals_yopal_token_2026")
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return str(challenge), 200
    return "Forbidden", 403


@app.route('/webhook', methods=['POST'])
def meta_webhook_handler():
    """Recepción en tiempo real de eventos de Instagram Graph API en la nube."""
    payload = request.json or {}
    log_event("aviso", "Meta Webhook", "Payload recibido desde Meta Graph API", "Cloud")
    return "EVENT_RECEIVED", 200


# -----------------------------------------------------------------------------
# INICIALIZACIÓN Y APERTURA DE NAVEGADOR
# -----------------------------------------------------------------------------

def abrir_navegador():
    time.sleep(1.2)
    webbrowser.open("http://localhost:5000")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    is_cloud = bool(os.environ.get("PORT") or os.environ.get("RENDER"))
    log_event("aviso", "Sistema", f"Servidor iniciado en puerto {port} ({'Modo Cloud 24/7' if is_cloud else 'Modo Local'}).", "Nube")
    
    # Asegurar que el hilo del bot de Instagram esté activo
    iniciar_hilo_bot_si_es_posible()
    
    # Abrir navegador automáticamente solo si estamos en local y no es recarga automática
    if not is_cloud and not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Thread(target=abrir_navegador, daemon=True).start()
    
    app.run(host='0.0.0.0', port=port, debug=False)
