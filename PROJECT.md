# Project: TapMeals Autonomous Business System (Yopal, Casanare)

## Architecture
The TapMeals Autonomous Business System is composed of four integrated layers designed to run 24/7 in the cloud (Render) and integrate with local/tunneled AI capabilities:

```
                               ┌────────────────────────────────────────────────────────┐
                               │             OMNIROUTE MODEL GATEWAY (:20128)           │
                               │        Claude Sonnet 5.5 / Gemini 3 Flash / Opus       │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                      ┌────────────────────────────────────┼────────────────────────────────────┐
                      ▼                                    ▼                                    ▼
       ┌─────────────────────────────┐      ┌─────────────────────────────┐      ┌─────────────────────────────┐
       │   LAYER 1: CLOUD RESPONDER  │      │  LAYER 2: AUTONOMOUS DEPTS  │      │   LAYER 3: MULTIMEDIA VIDEO │
       │   - app.py / Gunicorn       │      │  tapmeals_departments/      │      │   video_pipeline.py         │
       │   - /health (HTTP 200)      │      │  - ChefOps (10:30 Cut-off)  │      │   - 4-Beat Script Engine    │
       │   - /api/ai/query           │      │  - TrendRadar (Directives)  │      │   - Edge TTS (es-CO voices) │
       │   - instagrapi worker       │      │  - GrowthLead (Comment-to-DM│      │   - Pillow Overlay Cards    │
       │   - omniroute_client.py     │      │  - RetentionAgent (Feedback)│      │   - FFmpeg Fast Compositor  │
       └──────────────┬──────────────┘      └──────────────┬──────────────┘      └──────────────┬──────────────┘
                      │                                    │                                    │
                      └────────────────────────────────────┼────────────────────────────────────┘
                                                           ▼
                                            ┌─────────────────────────────┐
                                            │  LAYER 4: WEB PANEL & E2E   │
                                            │  - Panel Web UI Dashboard   │
                                            │  - Multimedia Tab & Player  │
                                            │  - E2E Test Suite (Tiers1-4)│
                                            └─────────────────────────────┘
```

## Feature Inventory
Every feature identified during the Survey phase is mapped to an implementation milestone:

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | OmniRoute Client Bridge | Standalone Python client supporting model routing (Claude Sonnet 5.5, Gemini 3 Flash) with retry and fallback | M1 | Survey 1 & 2 |
| 2 | Dynamic AI Messaging Handler | In `app.py` & `cloud_bot_worker.py`: replaces hardcoded static fallback with domain-grounded Claude/Gemini queries; strict reactive-only rule (only replies if user writes first, no proactive follower DMs, skips older msgs, checks msgs[0]) | M1 & M2 | Survey 1 & User Update |
| 3 | Cloud `/health` Endpoint | Returns HTTP 200 with worker status, uptime, and OmniRoute availability | M1 | Survey 1 |
| 4 | Multi-Model Query API | REST endpoint `/api/ai/query` allowing programmatic and frontend querying of Claude/Gemini | M1 | Survey 1 |
| 5 | Programmatic Connection Test | Script `probar_omniroute.py` executing live queries to port 20128 and confirming model outputs | M1 | Survey 1 |
| 6 | Cloud Sync & Render Config | Deployment scripts, environment configuration, and verification for Render cloud environment | M1 | Survey 1 |
| 7 | Kitchen Operations & MRP | `tapmeals_departments/chef_ops.py`: 10:30 AM cut-off reconciliation, raw ingredient calculations, route clustering | M2 | Survey 2 |
| 8 | Market Intelligence & Trends | `tapmeals_departments/trend_radar.py`: scrapes/evaluates health/fitness trends, outputs structured JSON directives | M2 | Survey 2 |
| 9 | Lead Acquisition & Growth | `tapmeals_departments/growth_lead.py`: Comment-to-DM (<3s), lead scoring (Cold/Warm/Hot), WhatsApp bridge | M2 | Survey 2 |
| 10 | Customer Retention & QA | `tapmeals_departments/retention_agent.py`: 1:45 PM feedback prompts, Friday subscription upgrades, win-back alerts | M2 | Survey 2 |
| 11 | Verified Business Economics | Standardized 305 g bowl (150 g chicken, 80 g rice, 75 g veggies), $13.500-$15.000 COP, 78 u/mo break-even, WhatsApp 573202337178 | M2 | Survey 2 |
| 12 | Departmental Dashboard UI | Integration of 4-department status and metrics into `index.html` and REST endpoints | M2 | Survey 2 |
| 13 | 4-Beat Video Script Generator | In `video_pipeline.py`: prompts OmniRoute for 16.0s viral Reel scripts tailored to Yopal fitness demographic | M3 | Survey 3 |
| 14 | Colombian Voice Synthesis | Uses Edge TTS with native Colombian voices (`es-CO-GonzaloNeural`, `es-CO-SalomeNeural`) | M3 | Survey 3 |
| 15 | Pillow Graphic Card Generator | Dynamically renders 1080x1920 transparent cards with brand colors (#F5A623, #09090B) and product specs | M3 | Survey 3 |
| 16 | FFmpeg Fast Compositor | Composites base video (`2_Reel_ApoloStyle_BASE_SIN_TEXTOS_CapCut.mp4`), overlays, and 120 BPM audio into 1080x1920 MP4 | M3 | Survey 3 |
| 17 | Studio Playwright Renderer | Headless Chromium renderer for interactive HTML templates (`5_Editor_Interactivo_TapMeals.html`) | M3 | Survey 3 |
| 18 | Web UI Multimedia Tab | Full multimedia panel tab with topic selector, reel generation triggers, built-in player, and asset download | M3 | Survey 3 |
| 19 | E2E Test Suite (Tiers 1-4) | Comprehensive test suite covering feature coverage, boundaries, combinatorial interactions, and real-world workloads | M4 | E2E Track |
| 20 | Cloud Operational Verification | Verification of live Render deployment returning HTTP 200 on `/health` and worker status | M4 | E2E Track |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Cloud Auto-Responder & OmniRoute Integration | `omniroute_client.py`, `app.py` AI integration, `/health` endpoint, `/api/ai/query`, `probar_omniroute.py` | None | DONE |
| 2 | M2: Autonomous Departments & Subagent Configurations | `tapmeals_departments/` (`chef_ops.py`, `trend_radar.py`, `growth_lead.py`, `retention_agent.py`), active trends registry, dashboard UI | M1 | IN_PROGRESS |
| 3 | M3: Automated Multimedia & Video Production Pipeline | `video_pipeline.py`, FFmpeg compositing, Edge TTS voiceover, Pillow overlays, web panel `tab-multimedia` | M1, M2 | PLANNED |
| 4 | M4: End-to-End Verification & Operational Readiness | 100% pass on E2E test suite (Tiers 1-4), adversarial hardening (Tier 5), Render verification | M1, M2, M3 | PLANNED |

## Interface Contracts

### OmniRoute Client ↔ Backend (`omniroute_client.py` ↔ `app.py`)
- `consultar_omniroute(prompt: str, model: str = "claude", system_prompt: str = None, timeout: int = 12) -> dict`
  - Input: prompt text, model alias (`"claude"` -> `agy/claude-sonnet-5-5-medium`, `"gemini"` -> `agy/gemini-3-flash`), optional system prompt.
  - Output: `{"success": bool, "response": str, "model": str, "latency": float, "error": str | None}`.
  - Error Handling: on network failure or timeout, returns `{"success": False, "response": fallback_text, "error": str}` without raising exceptions.

### Health Endpoint Contract (`app.py` `/health`)
- `GET /health`
  - Response: HTTP 200 Application/JSON
  - Schema:
    ```json
    {
      "status": "healthy" | "degraded",
      "service": "tapmeals-cloud-auto-responder",
      "worker_alive": bool,
      "ig_connected": bool,
      "ig_username": str,
      "uptime_seconds": int,
      "omniroute_available": bool,
      "departments_active": int
    }
    ```

### Trend Radar ↔ Video Pipeline (`trend_radar.py` ↔ `video_pipeline.py`)
- Standardized `TrendDirective` Schema:
  ```json
  {
    "trend_id": str,
    "topic": str,
    "category": str,
    "hook_angle": str,
    "product_specs_featured": {
      "weight_grams": 305,
      "chicken_grams": 150,
      "price_cop": "$13.500 - $15.000 COP",
      "packaging": "BOPS 3 divisiones"
    },
    "whatsapp_link": str,
    "cta_keyword": "TapTap"
  }
  ```

### Video Pipeline API (`video_pipeline.py` ↔ `app.py`)
- `generar_video_reel(topic: str, voice_id: str = "es-CO-GonzaloNeural", output_name: str = None) -> dict`
  - Output: `{"success": bool, "video_path": str, "duration": float, "resolution": "1080x1920", "script": dict, "error": str | None}`

## Code Layout
- `Panel_Web_TapMeals/`
  - `app.py`: Core web server, REST API, keepalive loop, health endpoints.
  - `cloud_bot_worker.py`: Background Instagram polling and session manager.
  - `omniroute_client.py`: Shared OmniRoute communication client with model fallbacks.
  - `probar_omniroute.py`: Test harness confirming port 20128 querying.
  - `tapmeals_departments/`:
    - `__init__.py`
    - `chef_ops.py`: Kitchen MRP & route clustering.
    - `trend_radar.py`: Market trend discovery & directive producer.
    - `growth_lead.py`: Comment-to-DM and lead scoring.
    - `retention_agent.py`: Post-delivery feedback & subscription retention.
  - `video_pipeline.py`: Automated video production engine (Script -> TTS -> Pillow -> FFmpeg).
  - `data/`:
    - `active_trends.json`: Active market trend directives registry.
    - `department_metrics.json`: Departmental activity metrics.
  - `static/videos/`: Output directory for generated MP4 reels and video previews.
  - `templates/index.html`: Web console dashboard with departments and multimedia tabs.
  - `tests/`:
    - `test_e2e_runner.py`: E2E test runner executing Tiers 1-4.
