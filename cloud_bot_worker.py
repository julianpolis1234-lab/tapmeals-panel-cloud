"""
===============================================================================
TAPMEALS CLOUD 24/7 AUTONOMOUS WORKER (@tapmeals.yopal)
Arquitectura Multi-Agente OmniRoute — Ejecución 100% en la Nube (GitHub Actions / Render)
Sin necesidad de tener el PC encendido.
===============================================================================
"""

import os
import sys
import time
import json
import base64
import random
from pathlib import Path
import urllib.request
import urllib.error

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
SESSION_FILE = BASE_DIR / "tapmeals_ig_session.json"
HISTORY_FILE = BASE_DIR / "taptap_processed_history.json"
DEFAULT_MENU_IMAGE = BASE_DIR / "Menu_Oficial_TapMeals_Yopal.png"

os.environ["TAPMEALS_CLOUD_WORKER_ONLY"] = "1"
from app import (
    cargar_config,
    cargar_historial,
    guardar_historial,
    evaluar_reglas,
)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "julianpolis1234-lab/tapmeals-panel-cloud").strip()
MAX_RUNTIME_SECONDS = int(os.environ.get("MAX_RUNTIME_SECONDS", "18000"))  # 5 horas por ciclo en GitHub Actions


def restore_session_from_env() -> bool:
    """Restaura tapmeals_ig_session.json desde el secreto encriptado TAPMEALS_IG_SESSION_B64."""
    b64_data = os.environ.get("TAPMEALS_IG_SESSION_B64", "").strip()
    if b64_data:
        try:
            raw = base64.b64decode(b64_data)
            SESSION_FILE.write_bytes(raw)
            print(f"[Cloud 24/7] Sesión restaurada desde TAPMEALS_IG_SESSION_B64 ({len(raw)} bytes).")
            return True
        except Exception as e:
            print(f"[Cloud 24/7] Error decodificando TAPMEALS_IG_SESSION_B64: {e}")
    if SESSION_FILE.exists():
        print(f"[Cloud 24/7] Usando archivo de sesión local: {SESSION_FILE.name}")
        return True
    print("[Cloud 24/7] ERROR: No se encontró TAPMEALS_IG_SESSION_B64 ni tapmeals_ig_session.json")
    return False


def pull_history_from_github(local_hist: dict) -> dict:
    """Sincroniza el historial procesado desde GitHub REST API para evitar duplicados entre contenedores."""
    if not GITHUB_TOKEN:
        return local_hist
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/taptap_processed_history.json"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "TapMeals-Cloud-Worker"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content_b64 = data.get("content", "")
            if content_b64:
                remote_hist = json.loads(base64.b64decode(content_b64).decode("utf-8"))
                for key in ["comentarios", "dms", "known_threads"]:
                    merged = list(dict.fromkeys(local_hist.get(key, []) + remote_hist.get(key, [])))
                    local_hist[key] = merged
                guardar_historial(local_hist)
    except Exception as e:
        print(f"[Cloud Sync] Aviso al descargar historial: {e}")
    return local_hist


def push_history_to_github(hist: dict):
    """Guarda taptap_processed_history.json en GitHub con [skip ci] tras responder un mensaje."""
    guardar_historial(hist)
    if not GITHUB_TOKEN:
        return
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/taptap_processed_history.json"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "TapMeals-Cloud-Worker",
        "Content-Type": "application/json"
    }
    try:
        sha = None
        req_get = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req_get, timeout=10) as resp:
                info = json.loads(resp.read().decode("utf-8"))
                sha = info.get("sha")
        except Exception:
            pass

        payload = {
            "message": "chore(cloud-bot): sync taptap_processed_history.json [skip ci]",
            "content": base64.b64encode(HISTORY_FILE.read_bytes()).decode("utf-8"),
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        req_put = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PUT"
        )
        with urllib.request.urlopen(req_put, timeout=12) as resp:
            if resp.status in (200, 201):
                print("[Cloud Sync] Historial sincronizado en GitHub correctamente.")
    except Exception as e:
        print(f"[Cloud Sync] Aviso al subir historial a GitHub: {e}")


def run_cloud_worker():
    print("==================================================================")
    print("🚀 INICIANDO TAPMEALS CLOUD 24/7 BOT (@tapmeals.yopal) - OMNIROUTE")
    print("==================================================================")

    if not restore_session_from_env():
        sys.exit(1)

    from instagrapi import Client

    cl = Client()
    cl.delay_range = [0.4, 0.9]

    try:
        cl.load_settings(SESSION_FILE)
        account = cl.account_info()
        my_user_id = str(account.pk)
        print(f"[Cloud 24/7] ✅ Conectado exitosamente a Instagram como @{account.username} (PK={my_user_id})")
    except Exception as e:
        print(f"[Cloud 24/7] ❌ Error validando sesión de Instagram: {e}")
        sys.exit(1)

    VERIFIED_KNOWN_THREADS = [
        "340282366841710301244259259610874989555",  # @julian.monroy10
        "340282366841710301244259647975719645042",  # @alitos0246
        "340282366841710301244259609051612611551",  # @juanf_elipemendoza
        "340282366841710301244259324659438433812",  # @tomassalazarrodriguez
        "340282366841710301244259265388784045112",  # @juan_garcia.64
        "340282366841710301244260000604202212981",  # @lucecita_2
        "340282366841710301244260346857080832537",  # @juanjose_vacagz
        "340282366841710301244259626122790867835",  # @danielmatiasprieto1
        "340282366841710301244260143586137853579",  # @gg8866760
    ]

    historial = pull_history_from_github(cargar_historial())
    dms_procesados = set(historial.get("dms", []))
    comentarios_procesados = set(historial.get("comentarios", []))
    known_threads = set(historial.get("known_threads", []))
    for vt in VERIFIED_KNOWN_THREADS:
        known_threads.add(vt)

    start_ts = time.time()
    circuit_breaker_until = 0
    cached_medias = []
    ultimo_refresh_medias = 0
    cooldown_threads = {}
    cooldown_seg = 6
    ciclo = 0

    while True:
        ahora = time.time()
        if MAX_RUNTIME_SECONDS > 0 and (ahora - start_ts) >= MAX_RUNTIME_SECONDS:
            print(f"[Cloud 24/7] Ciclo de {MAX_RUNTIME_SECONDS}s completado. Guardando estado y relevando al siguiente contenedor...")
            push_history_to_github(historial)
            break

        try:
            ciclo += 1
            conf = cargar_config()
            if ciclo % 25 == 0:
                historial = pull_history_from_github(historial)
                dms_procesados.update(historial.get("dms", []))
                comentarios_procesados.update(historial.get("comentarios", []))
                known_threads.update(historial.get("known_threads", []))

            # 1. COMENTARIOS EN REELS Y POSTS
            if ahora - ultimo_refresh_medias > 50 or not cached_medias:
                try:
                    all_m = []
                    try:
                        m_feed = cl.user_medias(cl.user_id, amount=3)
                        all_m.extend([m.pk for m in m_feed])
                    except Exception:
                        pass
                    try:
                        m_clips = cl.user_clips(cl.user_id, amount=3)
                        all_m.extend([clip.pk for clip in m_clips])
                    except Exception:
                        pass
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
                    comments = cl.media_comments(media_pk, amount=8)
                    our_replied_users = set()
                    for c_check in comments:
                        if str(c_check.user.pk) == my_user_id and c_check.text.startswith("@"):
                            first_tok = c_check.text.split()[0].lstrip("@").strip()
                            if first_tok:
                                our_replied_users.add(first_tok.lower())

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
                            print(f"[⚡ CLOUD COMENTARIO] @{username}: \"{c.text}\" -> {nombre_regla}")

                            comentarios_procesados.add(cid)
                            historial.setdefault("comentarios", []).append(cid)
                            push_history_to_github(historial)

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

                            try:
                                if dm_ok:
                                    pub = eval_res.get("comment_reply") or conf.get("comment_public_reply")
                                    resp = f"@{username} {pub}"
                                else:
                                    resp = f"@{username} {conf.get('closed_dms_reply')}"
                                try:
                                    cl.media_comment(media_pk, resp, replied_to_comment_id=c.pk)
                                except Exception:
                                    cl.media_comment(media_pk, resp)
                            except Exception as e_pub:
                                print(f"[Cloud Aviso Comentario] {e_pub}")
                except Exception:
                    pass

            # 2. SOLICITUDES DE MENSAJES (direct_pending_inbox)
            try:
                pending = cl.direct_pending_inbox(amount=5)
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
                        print(f"[⚡ CLOUD SOLICITUD] @{username}: \"{m.text}\" -> {nombre_regla}")

                        dms_procesados.add(m_id)
                        historial.setdefault("dms", []).append(m_id)
                        push_history_to_github(historial)

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

            # 3. HILOS CONOCIDOS (Round-Robin)
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
                                print(f"[⚡ CLOUD DM] @{username}: \"{m.text}\" -> {nombre_regla}")

                                dms_procesados.add(mid)
                                historial.setdefault("dms", []).append(mid)
                                push_history_to_github(historial)

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

            # 4. BANDEJA PRINCIPAL (direct_threads con Circuit Breaker)
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
                            if str(m.user_id) == my_user_id:
                                break
                            mid = str(m.id)
                            if mid in dms_procesados:
                                continue

                            eval_res = evaluar_reglas(m.text, "dm", conf)
                            if eval_res.get("triggers"):
                                user = thread.users[0] if thread.users else None
                                username = user.username if user else "atleta"
                                regla = eval_res.get("rule")
                                nombre_regla = regla["name"] if regla else "Regla DM"
                                print(f"[⚡ CLOUD INBOX DM] @{username}: \"{m.text}\" -> {nombre_regla}")

                                dms_procesados.add(mid)
                                historial.setdefault("dms", []).append(mid)
                                push_history_to_github(historial)
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

            if ciclo == 1 or ciclo % 20 == 0:
                print(f"[Cloud 24/7 Heartbeat] Ciclo #{ciclo} OK | Hilos monitoreados: {len(known_threads)} | DMs procesados: {len(dms_procesados)} | Comentarios procesados: {len(comentarios_procesados)}")

            time.sleep(random.uniform(1.8, 2.6))

        except Exception as e_loop:
            print(f"[Cloud 24/7 Loop Aviso] {e_loop}")
            time.sleep(3)


if __name__ == "__main__":
    run_cloud_worker()
