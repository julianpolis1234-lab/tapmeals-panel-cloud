"""
===============================================================================
PANEL DE CONTROL WEB Y SERVIDOR CLOUD 24/7 — TAPMEALS (@tapmeals.yopal)
===============================================================================
Servidor Flask con API REST y Dashboard Administrativo:
- Monitoreo en tiempo real del estado del bot (24/7)
- Editor interactivo de mensajes, disparadores 'TapTap' y macros
- Simulador de chat en vivo para probar respuestas
- Registro de actividad e interacciones de clientes
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
HISTORY_FILE = PROJECT_DIR / "taptap_processed_history.json"
if not HISTORY_FILE.exists():
    HISTORY_FILE = BASE_DIR / "taptap_processed_history.json"

DEFAULT_MENU_IMAGE = BASE_DIR / "Menu_Oficial_TapMeals_Yopal.png"
if not DEFAULT_MENU_IMAGE.exists():
    DEFAULT_MENU_IMAGE = KIT_DIR / "Menu_Oficial_TapMeals_Yopal.png"

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

# Estado en memoria
server_start_time = time.time()
bot_logs = []
bot_worker_thread = None
bot_running_flag = False


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
    if not texto:
        return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()


def verificar_taptap(texto: str) -> bool:
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


def cargar_config() -> dict:
    default_config = {
        "bot_enabled": True,
        "trigger_keyword": "TapTap",
        "welcome_message": "¡Hola atleta! 🍱⚡ Aquí tienes el menú oficial de TapMeals en Yopal.\n\n💡 Cero fritos ni aceites quemados. Cada bandeja viene pesada en báscula digital con etiqueta sellada en la tapa.",
        "comment_public_reply": "¡Te acabamos de enviar el menú oficial por mensaje directo! Revisa tu DM 🍱⚡",
        "closed_dms_reply": "Tu cuenta tiene bloqueados los DMs de externos 🔒 Porfa envíanos tú un mensaje al directo con la palabra 'TapTap' y te llegará la carta de una 🍱⚡",
        "cooldown_seconds": 45,
        "scan_interval_seconds": 1.5,
        "menu_image_path": str(DEFAULT_MENU_IMAGE),
        "cloud_mode": "manychat_recommended"
    }
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            default_config.update(saved)
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
    return {"comentarios": [], "dms": []}


# -----------------------------------------------------------------------------
# RUTAS DE LA INTERFAZ WEB (FRONTEND)
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template("index.html")


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
        "logs_count": len(bot_logs),
        "cloud_mode": conf.get("cloud_mode", "manychat_recommended"),
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route('/api/toggle-bot', methods=['POST'])
def toggle_bot():
    conf = cargar_config()
    nuevo_estado = not conf.get("bot_enabled", True)
    conf["bot_enabled"] = nuevo_estado
    guardar_config(conf)
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
        log_event("exito", "Configuración", "Ajustes de mensajes y disparadores actualizados con éxito.", "Ajustes")
        return jsonify({"success": True, "config": conf})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/upload-menu', methods=['POST'])
def upload_menu():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No se envió ningún archivo"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "Nombre de archivo vacío"}), 400
    
    filename = secure_filename(file.filename)
    dest_path = KIT_DIR / "Menu_Oficial_TapMeals_Yopal.png"
    file.save(dest_path)
    
    conf = cargar_config()
    conf["menu_image_path"] = str(dest_path)
    guardar_config(conf)
    
    log_event("exito", "Menú", "Nueva imagen del menú oficial subida y actualizada en el contestador.", "Carta")
    return jsonify({"success": True, "path": str(dest_path)})


@app.route('/api/test-simulator', methods=['POST'])
def test_simulator():
    """Simula en tiempo real la respuesta exacta del bot para cualquier mensaje."""
    data = request.json or {}
    texto = data.get("text", "")
    tipo_canal = data.get("channel", "dm") # 'dm', 'solicitud', 'comentario'
    
    conf = cargar_config()
    es_taptap = verificar_taptap(texto)
    es_solicitud = es_solicitud_menu(texto)
    
    if tipo_canal in ["dm", "solicitud"]:
        if es_solicitud:
            log_event("exito", "@atleta_simulado", f"Simulación DM: \"{texto}\" -> Menú enviado", "Simulador")
            return jsonify({
                "triggers": True,
                "reason": "Coincide con 'TapTap' o petición de menú",
                "dm_response": conf.get("welcome_message"),
                "has_image": True,
                "image_url": "/menu-image",
                "approved_request": (tipo_canal == "solicitud")
            })
        else:
            return jsonify({
                "triggers": False,
                "reason": "El mensaje no contiene 'TapTap' ni palabras clave de menú",
                "dm_response": None,
                "has_image": False
            })
    else: # comentario
        if es_taptap:
            log_event("comentario", "@atleta_simulado", f"Simulación Comentario: \"{texto}\" -> Respondido", "Simulador")
            return jsonify({
                "triggers": True,
                "reason": "Detectó 'TapTap' en comentario de publicación",
                "public_comment_reply": f"@atleta_simulado {conf.get('comment_public_reply')}",
                "dm_response": conf.get("welcome_message"),
                "has_image": True,
                "image_url": "/menu-image"
            })
        else:
            return jsonify({
                "triggers": False,
                "reason": "El comentario no contiene la palabra clave 'TapTap'",
                "public_comment_reply": None
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
# INICIALIZACIÓN Y APERTURA DE NAVEGADOR
# -----------------------------------------------------------------------------

def abrir_navegador():
    time.sleep(1.2)
    webbrowser.open("http://localhost:5000")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    is_cloud = bool(os.environ.get("PORT") or os.environ.get("RENDER"))
    log_event("aviso", "Sistema", f"Servidor iniciado en puerto {port} ({'Modo Cloud 24/7' if is_cloud else 'Modo Local'}).", "Nube")
    
    # Abrir navegador automáticamente solo si estamos en local y no es recarga automática
    if not is_cloud and not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Thread(target=abrir_navegador, daemon=True).start()
    
    app.run(host='0.0.0.0', port=port, debug=False)
