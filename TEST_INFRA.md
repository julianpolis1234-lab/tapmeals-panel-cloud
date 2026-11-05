# E2E Test Infra: TapMeals Autonomous Business System

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Derives tests directly from `ORIGINAL_REQUEST.md` and user requirements.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial + Real-World Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | OmniRoute Port 20128 Client | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | Dynamic AI Auto-Responder | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | Cloud /health Endpoint (HTTP 200) | ORIGINAL_REQUEST §AC | 5 | 5 | ✓ |
| 4 | Multi-Model Query API (/api/ai/query) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 5 | Programmatic Connection Test (probar_omniroute.py) | ORIGINAL_REQUEST §AC | 5 | 5 | ✓ |
| 6 | Cloud Sync & Render Config | ORIGINAL_REQUEST §AC | 5 | 5 | ✓ |
| 7 | Kitchen Operations & MRP (10:30 AM Cutoff) | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 8 | Market Intelligence & Trend Radar Directives | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 9 | Lead Acquisition (Comment-to-DM <3s) | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 10 | Customer Retention & Quality Assurance | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 11 | Verified Business Specs (305g, $13.500-$15.000) | ORIGINAL_REQUEST §AC | 5 | 5 | ✓ |
| 12 | Departmental Dashboard UI Integration | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 13 | 4-Beat Video Script Generator | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 14 | Colombian Voice Synthesis (Edge TTS) | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 15 | Pillow Graphic Card Generator (1080x1920) | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 16 | FFmpeg Fast Compositor (MP4 Output) | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 17 | Studio Playwright Renderer Fallback | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 18 | Web UI Multimedia Tab & Player | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 19 | Bot Session Handling & Loop Stability | ORIGINAL_REQUEST §AC | 5 | 5 | ✓ |
| 20 | Live Render Cloud Health Check | ORIGINAL_REQUEST §AC | 5 | 5 | ✓ |

## Test Architecture
- Test runner: `python tests/test_e2e_runner.py`
- Pass/Fail Semantics: Exit code 0 on all tests passing; non-zero on any failure.
- Directory layout:
  - `Panel_Web_TapMeals/tests/test_e2e_runner.py` (Master test runner)
  - `Panel_Web_TapMeals/tests/test_tier1_features.py`
  - `Panel_Web_TapMeals/tests/test_tier2_boundaries.py`
  - `Panel_Web_TapMeals/tests/test_tier3_combinations.py`
  - `Panel_Web_TapMeals/tests/test_tier4_scenarios.py`

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Gym athlete asks for high-protein lunch in Yopal via DM | F1, F2, F9, F11 | Medium |
| 2 | Kitchen 10:30 AM cutoff triggers MRP explosion for 85 orders | F7, F11 | Medium |
| 3 | Viral trend on afternoon fatigue generates complete 16s video | F8, F13, F14, F15, F16, F11 | High |
| 4 | Cloud health monitoring and failover when OmniRoute is offline | F1, F2, F3, F6 | High |
| 5 | End-to-end customer journey from Comment "TapTap" to WhatsApp | F9, F10, F11, F12 | High |

## Coverage Thresholds
- Tier 1: ≥5 per feature (20 features × 5 = 100 test cases)
- Tier 2: ≥5 per feature (20 features × 5 = 100 boundary tests)
- Tier 3: Pairwise coverage across major feature interactions (≥20 tests)
- Tier 4: ≥5 realistic end-to-end application scenarios
- **Total: ~225 test cases**
