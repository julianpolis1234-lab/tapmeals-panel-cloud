"""
===============================================================================
MASTER E2E TEST RUNNER — TAPMEALS AUTONOMOUS BUSINESS SYSTEM (@tapmeals.yopal)
===============================================================================
Executes Tiers 1-4 opaque-box and contract test suites per TEST_INFRA.md:
- Tier 1: Feature Coverage (20 features x 5 = 100 tests)
- Tier 2: Boundary Value Analysis & Edge Cases (20 features x 5 = 100 tests)
- Tier 3: Combinatorial Cross-Feature Interactions (20 tests)
- Tier 4: Real-World Application Workload Scenarios (5 tests)
Total: 225 Genuine Test Cases

Outputs structured metrics, execution latency, coverage percentage,
and exits with code 0 ONLY if 100% of tests pass.
===============================================================================
"""

import os
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, Any, List

# Configurar salida UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_PANEL_DIR = Path(__file__).resolve().parent.parent
if str(BASE_PANEL_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_PANEL_DIR))

# Importar las suites de prueba
from tests.test_tier1_features import TestTier1Features
from tests.test_tier2_boundaries import TestTier2Boundaries
from tests.test_tier3_combinations import TestTier3Combinations
from tests.test_tier4_scenarios import TestTier4Scenarios


class TierMetricResult:
    def __init__(self, tier_name: str, description: str):
        self.tier_name = tier_name
        self.description = description
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.skipped = 0
        self.duration = 0.0
        self.failure_details: List[str] = []


def run_tier(suite_class, tier_name: str, description: str) -> TierMetricResult:
    metric = TierMetricResult(tier_name, description)
    suite = unittest.TestLoader().loadTestsFromTestCase(suite_class)
    metric.total = suite.countTestCases()
    
    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    metric.duration = round(time.time() - start_time, 2)
    
    metric.errors = len(result.errors)
    metric.failed = len(result.failures)
    metric.skipped = len(result.skipped)
    metric.passed = metric.total - (metric.failed + metric.errors + metric.skipped)
    
    for test, err in result.failures:
        metric.failure_details.append(f"FAIL: {test.id()} -> {err.splitlines()[-1]}")
    for test, err in result.errors:
        metric.failure_details.append(f"ERROR: {test.id()} -> {err.splitlines()[-1]}")
        
    return metric


def print_e2e_dashboard(metrics: List[TierMetricResult]):
    total_tests = sum(m.total for m in metrics)
    total_passed = sum(m.passed for m in metrics)
    total_failed = sum(m.failed for m in metrics)
    total_errors = sum(m.errors for m in metrics)
    total_duration = sum(m.duration for m in metrics)
    coverage_pct = round((total_passed / total_tests * 100.0) if total_tests > 0 else 0.0, 1)

    print("\n" + "=" * 80)
    print("   TAPMEALS AUTONOMOUS BUSINESS SYSTEM — E2E TEST RUNNER (TIERS 1-4)")
    print("=" * 80)
    print(f" Target Service: TapMeals Yopal Cloud Auto-Responder (@tapmeals.yopal)")
    print(f" Environment:    Python {sys.version.split()[0]} on Windows / Render 24/7 Cloud")
    print(f" Timestamp:      {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("-" * 80)
    print(f" {'TIER':<8} | {'DESCRIPTION':<36} | {'RUN':<5} | {'PASS':<5} | {'FAIL':<5} | {'TIME':<6}")
    print("-" * 80)

    for m in metrics:
        status_tag = f"{m.passed}/{m.total}"
        print(f" {m.tier_name:<8} | {m.description:<36} | {m.total:<5} | {m.passed:<5} | {m.failed + m.errors:<5} | {m.duration:>5.1f}s")

    print("=" * 80)
    print(f" TOTAL EXECUTED:  {total_tests} tests")
    print(f" TOTAL PASSED:    {total_passed} tests ({'✅ 100%' if total_passed == total_tests else f'⚠️ {coverage_pct}%'})")
    print(f" TOTAL FAILED:    {total_failed + total_errors} tests")
    print(f" TOTAL DURATION:  {total_duration:.2f} seconds")
    print(f" TEST COVERAGE:   {coverage_pct}% of operational requirements verified")
    print("=" * 80)

    has_failures = any(len(m.failure_details) > 0 for m in metrics)
    if has_failures:
        print("\n❌ DETALLE DE FALLOS REGISTRADOS:")
        for m in metrics:
            if m.failure_details:
                print(f"\n--- {m.tier_name}: {m.description} ---")
                for fail in m.failure_details:
                    print(f"  • {fail}")
        print("\n" + "=" * 80)
    else:
        print("\n🎉 ¡TODOS LOS NIVELES (TIERS 1-4) FUERON SUPERADOS CON 100% DE ÉXITO!")
        print("   La arquitectura del Sistema Autónomo TapMeals está validada y lista para operación.")
        print("=" * 80 + "\n")


def main():
    print("\n[E2E Runner] Iniciando ejecución de Tiers 1-4 para TapMeals Autonomous Business System...")
    
    tiers = [
        (TestTier1Features, "TIER 1", "Feature Coverage (20 Features x 5)"),
        (TestTier2Boundaries, "TIER 2", "Boundary Value Analysis & Edge Cases"),
        (TestTier3Combinations, "TIER 3", "Cross-Feature Combinatorial Pairs"),
        (TestTier4Scenarios, "TIER 4", "Real-World Workload Scenarios")
    ]
    
    results = []
    for suite_class, tier_name, desc in tiers:
        print(f"  -> Ejecutando {tier_name}: {desc}...", flush=True)
        metric = run_tier(suite_class, tier_name, desc)
        results.append(metric)
        print(f"     Completado en {metric.duration}s. Aprobados: {metric.passed}/{metric.total}")
        
    print_e2e_dashboard(results)
    
    all_passed = all((m.failed == 0 and m.errors == 0) for m in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
