"""
Master Test Runner — PrivateVault Integration
Runs all 4 test suites and generates a comprehensive summary report.
"""

import sys
import os
import json
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from privatevault.audit_ledger import AuditLedger

from test_prompt_injection import run_prompt_injection_tests, print_results as print_t1
from test_context_poisoning import run_context_poisoning_tests, print_results as print_t2
from test_sensitive_data import run_sensitive_data_tests, print_results as print_t3
from test_hallucination import run_hallucination_tests, print_results as print_t4


def run_all_tests():
    """Execute all test suites with a shared audit ledger."""
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█  PRIVATEVAULT INTEGRATION — COMPREHENSIVE SECURITY TEST SUITE    █")
    print("█  Credit Risk AI Lending Decision Support System                  █")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    os.makedirs("results", exist_ok=True)

    ledger = AuditLedger(log_file="results/audit_ledger_master.jsonl")

    ledger.log_event(
        event_type="TEST_SUITE_START",
        data={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tests": ["prompt_injection", "context_poisoning", "sensitive_data", "hallucination"],
        },
        outcome="STARTED",
    )

    start_time = time.time()
    all_results = {}

    print("\n\n  ▶ Running Test 1: Prompt Injection Attacks...")
    t1_start = time.time()
    t1_results = run_prompt_injection_tests(ledger)
    t1_time = time.time() - t1_start
    print_t1(t1_results)
    all_results["test1_prompt_injection"] = t1_results
    with open("results/test1_prompt_injection.json", "w") as f:
        json.dump(t1_results, f, indent=2)
    print(f"  ✓ Test 1 completed in {t1_time:.2f}s")

    print("\n\n  ▶ Running Test 2: Context Poisoning...")
    t2_start = time.time()
    t2_results = run_context_poisoning_tests(ledger)
    t2_time = time.time() - t2_start
    print_t2(t2_results)
    all_results["test2_context_poisoning"] = t2_results
    with open("results/test2_context_poisoning.json", "w") as f:
        json.dump(t2_results, f, indent=2)
    print(f"  ✓ Test 2 completed in {t2_time:.2f}s")

    print("\n\n  ▶ Running Test 3: Sensitive Data Protection...")
    t3_start = time.time()
    t3_results = run_sensitive_data_tests(ledger)
    t3_time = time.time() - t3_start
    print_t3(t3_results)
    all_results["test3_sensitive_data"] = t3_results
    with open("results/test3_sensitive_data.json", "w") as f:
        json.dump(t3_results, f, indent=2)
    print(f"  ✓ Test 3 completed in {t3_time:.2f}s")

    print("\n\n  ▶ Running Test 4: Hallucination & Decision Integrity...")
    t4_start = time.time()
    t4_results = run_hallucination_tests(ledger)
    t4_time = time.time() - t4_start
    print_t4(t4_results)
    all_results["test4_hallucination"] = t4_results
    with open("results/test4_hallucination.json", "w") as f:
        json.dump(t4_results, f, indent=2)
    print(f"  ✓ Test 4 completed in {t4_time:.2f}s")

    total_time = time.time() - start_time

    summary = {
        "test_suite": "PrivateVault Integration — Security Test Suite",
        "system": "Credit Risk AI Lending Decision Support",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_execution_time_seconds": round(total_time, 2),
        "results_summary": {
            "test1_prompt_injection": {
                "attacks_tested": t1_results["total_attacks"],
                "blocked_without_pv": "0/7 (0%)",
                "blocked_with_pv": t1_results["block_rate_with_pv"],
            },
            "test2_context_poisoning": {
                "scenarios_tested": t2_results["total_scenarios"],
                "detected_without_pv": "0/4 (0%)",
                "detected_with_pv": t2_results["detection_rate_with_pv"],
            },
            "test3_sensitive_data": {
                "scenarios_tested": t3_results["total_scenarios"],
                "protected_without_pv": "0/8 (0%)",
                "protected_with_pv": t3_results["protection_rate_with_pv"],
            },
            "test4_hallucination": {
                "cases_tested": t4_results["total_test_cases"],
                "issues_caught": t4_results["issues_caught_by_pv"],
                "catch_rate": t4_results["reliability_improvement"]["catch_rate"],
            },
        },
        "audit_ledger": ledger.get_summary(),
        "audit_chain_integrity": ledger.verify_integrity(),
    }

    with open("results/summary_report.json", "w") as f:
        json.dump(summary, f, indent=2)

    with open("results/audit_ledger_readable.txt", "w") as f:
        f.write(ledger.export_human_readable())

    print("\n\n" + "█" * 70)
    print("█  COMPREHENSIVE RESULTS SUMMARY                                   █")
    print("█" * 70)

    print(f"""
  ┌──────────────────────────────────────────────────────────────────┐
  │  TEST                    │ WITHOUT PV     │ WITH PV              │
  ├──────────────────────────┼────────────────┼──────────────────────┤
  │  1. Prompt Injection     │ 0/7 blocked    │ {t1_results['block_rate_with_pv']:<20s} │
  │  2. Context Poisoning    │ 0/4 detected   │ {t2_results['detection_rate_with_pv']:<20s} │
  │  3. Sensitive Data       │ 0/8 protected  │ {t3_results['protection_rate_with_pv']:<20s} │
  │  4. Hallucination Check  │ 0/20 validated │ {t4_results['reliability_improvement']['catch_rate']+ ' caught':<20s} │
  └──────────────────────────┴────────────────┴──────────────────────┘

  Audit Ledger: {ledger.get_summary()['total_entries']} entries | Chain Integrity: {'✓ VALID' if ledger.verify_integrity()['is_valid'] else '✗ BROKEN'}
  Total Execution Time: {total_time:.2f}s

  Files Generated:
    → results/test1_prompt_injection.json
    → results/test2_context_poisoning.json
    → results/test3_sensitive_data.json
    → results/test4_hallucination.json
    → results/summary_report.json
    → results/audit_ledger_master.jsonl
    → results/audit_ledger_readable.txt
""")

    print("█" * 70)
    print("█  ALL TESTS COMPLETE                                              █")
    print("█" * 70 + "\n")

    return summary


if __name__ == "__main__":
    run_all_tests()
