"""
===============================================================================
TAPMEALS AUTOMATED VIDEO & MULTIMEDIA PRODUCTION PIPELINE (M3)
===============================================================================
- 4-Beat Viral Reel Script Generator (16.0s total) via OmniRoute (con cascada gratuita)
- Síntesis de voz neuronal colombiana (Edge TTS: es-CO-GonzaloNeural / es-CO-SalomeNeural)
- Generador de tarjetas gráficas RGBA 1080x1920 con Pillow (#F5A623, #09090B, #141418)
- Compositor rápido FFmpeg (libx264, yuv420p, +faststart, 1080x1920)
===============================================================================
"""

import os
import json
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
KIT_DIR = BASE_DIR.parent
VIDEOS_DIR = BASE_DIR / "static" / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

BASE_VIDEO_PATH = KIT_DIR / "2_Reel_ApoloStyle_BASE_SIN_TEXTOS_CapCut.mp4"
AUDIO_BEAT_PATH = KIT_DIR / "4_Stickers_y_Audios" / "Audio_Beat_120BPM.mp3"
STICKER_LOGO_PATH = KIT_DIR / "4_Stickers_y_Audios" / "Sticker_Logo_TapMeals_Transparente.png"
STICKER_BOWL_PATH = KIT_DIR / "4_Stickers_y_Audios" / "Sticker_Bowl_TapMeals_Transparente.png"

VOICE_COLOMBIA_MALE = "es-CO-GonzaloNeural"
VOICE_COLOMBIA_FEMALE = "es-CO-SalomeNeural"

BRAND_COLOR_GOLD = "#F5A623"
BRAND_COLOR_BG = "#09090B"
BRAND_COLOR_PANEL = "#141418"


def _default_4beat_script(topic: str) -> Dict[str, Any]:
    topic_clean = (topic or "proteina real 305g").strip()
    return {
        "topic": topic_clean,
        "total_duration": 16.0,
        "product_specs": {
            "weight_grams": 305,
            "chicken_grams": 150,
            "rice_grams": 80,
            "veggies_grams": 75,
            "price_range": "$13.500 - $15.000 COP",
            "whatsapp": "573202337178",
            "packaging": "BOPS 3 divisiones"
        },
        "beats": [
            {
                "beat_number": 1,
                "time_start": 0.0,
                "time_end": 4.0,
                "spoken_text": f"¿Cansado del corrientazo grasoso en Yopal cuando buscas {topic_clean[:35]}?",
                "visual_headline": "¿CORRIENTAZO GRASOSO?",
                "visual_sub": "El 38% en Yopal no sabe cuanta proteina come"
            },
            {
                "beat_number": 2,
                "time_start": 4.0,
                "time_end": 8.0,
                "spoken_text": "En TapMeals pesamos 305 gramos reales: 150 de pechuga magra, 80 de arroz y 75 de vegetales.",
                "visual_headline": "305g REALES EN BASCULA",
                "visual_sub": "150g pechuga + 80g arroz + 75g vegetales"
            },
            {
                "beat_number": 3,
                "time_start": 8.0,
                "time_end": 12.0,
                "spoken_text": "Empaque BOPS de 3 divisiones con etiqueta nutricional verificada y cero aceites quemados.",
                "visual_headline": "EMPAQUE BOPS 3 DIVISIONES",
                "visual_sub": "38g proteina real · Cero aceites quemados"
            },
            {
                "beat_number": 4,
                "time_start": 12.0,
                "time_end": 16.0,
                "spoken_text": "Desde trece mil quinientos pesos en Yopal. Comenta TapTap o escribe al WhatsApp 3202337178.",
                "visual_headline": "$13.500 - $15.000 COP",
                "visual_sub": "Comenta 'TapTap' · WhatsApp 573202337178"
            }
        ]
    }


def generate_4beat_script(topic: str, use_ai: bool = False, model: str = "ddgw/claude-haiku-4-5") -> Dict[str, Any]:
    """
    Genera un guión estructurado de 4 beats (16.0s total) con los datos reales de TapMeals
    (305g, 150g pechuga, $13.500-$15.000 COP, WhatsApp 573202337178, TapTap).
    Usa plantilla instantánea verificada o consulta el modelo gratuito en OmniRoute si use_ai=True.
    """
    base = _default_4beat_script(topic)
    if not use_ai:
        return base
    try:
        from omniroute_client import consultar_omniroute
        prompt = (
            f"Genera un frase corta de gancho (max 14 palabras) para un Reel sobre '{topic}' "
            "de TapMeals en Yopal (305g reales, 150g pechuga, $13.500-$15.000 COP)."
        )
        res = consultar_omniroute(prompt, model=model, timeout=6)
        if res.get("success") and res.get("response"):
            hook_line = res["response"].splitlines()[0].strip().strip('"')[:95]
            if len(hook_line) > 10:
                base["beats"][0]["spoken_text"] = hook_line
    except Exception:
        pass
    return base


def render_overlay_card(
    headline: str,
    subtext: str,
    output_path: Path,
    width: int = 1080,
    height: int = 1920
) -> Path:
    """Genera una tarjeta gráfica RGBA transparente (esquina (0,0) con alpha=0)."""
    from PIL import Image, ImageDraw

    output_path = Path(output_path)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    card_top = int(height * 0.68)
    card_bottom = int(height * 0.84)
    card_left = int(width * 0.08)
    card_right = int(width * 0.92)

    draw.rounded_rectangle(
        [(card_left, card_top), (card_right, card_bottom)],
        radius=36,
        fill=(20, 20, 24, 228),
        outline=(245, 166, 35, 255),
        width=6
    )
    draw.text((card_left + 44, card_top + 48), str(headline)[:80], fill=(245, 166, 35, 255))
    draw.text((card_left + 44, card_top + 115), str(subtext)[:100], fill=(255, 255, 255, 255))
    draw.text((card_left + 44, card_top + 175), "TapMeals Yopal · 305g Reales · $13.500-$15.000 COP · WA 573202337178", fill=(16, 185, 129, 255))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    return output_path


def synthesize_voiceover(text: str, output_mp3: Path, voice_id: str = VOICE_COLOMBIA_MALE) -> bool:
    """Sintetiza locución en español colombiano con Edge TTS."""
    output_mp3 = Path(output_mp3)
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    try:
        import edge_tts

        async def _run():
            comm = edge_tts.Communicate(text, voice_id)
            await comm.save(str(output_mp3))

        asyncio.run(_run())
        return output_mp3.exists() and output_mp3.stat().st_size > 400
    except Exception:
        return False


def generar_video_reel(
    topic: str = "Almuerzo Fitness 305g Yopal",
    voice_id: str = VOICE_COLOMBIA_MALE,
    output_name: Optional[str] = None,
    use_ai: bool = False
) -> Dict[str, Any]:
    """
    Pipeline completo M3:
    1. Genera guion de 4 beats (16.0s) con especificaciones verificadas de TapMeals.
    2. Renderiza tarjeta gráfica RGBA 1080x1920 con Pillow.
    3. Sintetiza locución colombiana (o usa locución maestra de respaldo).
    4. Compone el MP4 final 1080x1920 con FFmpeg (+faststart, libx264, yuv420p).
    """
    t0 = time.time()
    script = generate_4beat_script(topic, use_ai=use_ai)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    safe_slug = "".join(c if c.isalnum() else "_" for c in (output_name or topic))[:36].strip("_") or "reel"
    if not safe_slug.endswith(".mp4"):
        filename = f"tapmeals_{safe_slug}.mp4"
    else:
        filename = safe_slug
    out_video = VIDEOS_DIR / filename

    card_path = VIDEOS_DIR / f"_card_{safe_slug}.png"
    voice_path = VIDEOS_DIR / f"_voice_{safe_slug}.mp3"

    try:
        b1 = script["beats"][0]
        render_overlay_card(b1["visual_headline"], b1["visual_sub"], card_path, 1080, 1920)

        full_narration = " ".join(b["spoken_text"] for b in script["beats"])
        tts_ok = synthesize_voiceover(full_narration, voice_path, voice_id=voice_id)

        if BASE_VIDEO_PATH.exists():
            cmd = [
                "ffmpeg", "-y",
                "-i", str(BASE_VIDEO_PATH),
                "-i", str(card_path),
            ]
            if tts_ok and voice_path.exists():
                cmd.extend(["-i", str(voice_path)])
                cmd.extend([
                    "-filter_complex", "[0:v][1:v]overlay=0:0:enable='between(t,0,16)'[vout];[2:a]volume=1.0[aout]",
                    "-map", "[vout]", "-map", "[aout]",
                ])
            else:
                cmd.extend([
                    "-filter_complex", "[0:v][1:v]overlay=0:0:enable='between(t,0,16)'[vout]",
                    "-map", "[vout]", "-map", "0:a?",
                ])
            cmd.extend([
                "-t", "16",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(out_video)
            ])
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode != 0:
                return {
                    "success": False,
                    "video_path": str(out_video),
                    "duration": 16.0,
                    "resolution": "1080x1920",
                    "script": script,
                    "error": proc.stderr[-300:]
                }
        else:
            # Fallback si el video base no está en un contenedor cloud ligero
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-t", "4", "-i", str(card_path),
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(out_video)
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=45)

        return {
            "success": out_video.exists() and out_video.stat().st_size > 1000,
            "video_path": str(out_video),
            "video_url": f"/static/videos/{out_video.name}",
            "filename": out_video.name,
            "size_bytes": out_video.stat().st_size if out_video.exists() else 0,
            "duration": 16.0,
            "resolution": "1080x1920",
            "elapsed_sec": round(time.time() - t0, 2),
            "script": script,
            "error": None
        }
    finally:
        for tmp in (card_path, voice_path):
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass


def listar_videos_generados() -> list:
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for f in sorted(VIDEOS_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        items.append({
            "filename": f.name,
            "url": f"/static/videos/{f.name}",
            "size_kb": round(f.stat().st_size / 1024, 1),
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))
        })
    return items
