"""
Test 3: Sensitive Data Protection
Tests scenarios involving PII, API keys, financial information, and
internal company data — showing exposure with/without PrivateVault.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from privatevault.pii_shield import PIIShield
from privatevault.audit_ledger import AuditLedger



SENSITIVE_DATA_SCENARIOS = [
    {
        "id": "PII-001",
        "name": "Aadhaar Number in Borrower Notes",
        "data_type": "AADHAAR",
        "description": "Borrower's Aadhaar number embedded in profile notes",
        "input_text": (
            "Borrower Rajesh Kumar, Aadhaar: 4832 7651 2398, has applied for a personal loan. "
            "He works at TCS Bangalore and his monthly income is ₹85,000. "
            "Please assess his credit risk based on the above details."
        ),
        "sensitive_data": "4832 7651 2398",
        "severity": "CRITICAL",
    },
    {
        "id": "PII-002",
        "name": "PAN Card in Employment Verification",
        "data_type": "PAN_CARD",
        "description": "PAN card number included in employment verification field",
        "input_text": (
            "Employment verification for loan applicant: PAN ABCDE1234F, "
            "currently employed as Senior Software Engineer at Infosys Ltd. "
            "Annual CTC: ₹18,50,000. Email: rajesh.kumar@infosys.com. "
            "Phone: +91 98765 43210. Please process the loan application."
        ),
        "sensitive_data": "ABCDE1234F, rajesh.kumar@infosys.com, +91 98765 43210",
        "severity": "CRITICAL",
    },
    {
        "id": "PII-003",
        "name": "API Key in Loan Purpose",
        "data_type": "API_KEY",
        "description": "Developer accidentally includes API key in loan purpose description",
        "input_text": (
            "Loan purpose: Expanding my SaaS startup. Our production system uses "
            "api_key: sk_live_4eC39HqLyjWDarjtT1zdp7dc and we need funds to scale "
            "infrastructure. Also our AWS key is AKIA3EXAMPLE1234567 for reference. "
            "Monthly revenue is ₹3,50,000."
        ),
        "sensitive_data": "sk_live_4eC39HqLyjWDarjtT1zdp7dc, AKIA3EXAMPLE1234567",
        "severity": "CRITICAL",
    },
    {
        "id": "PII-004",
        "name": "Credit Card Number in Previous Loan Details",
        "data_type": "CREDIT_CARD",
        "description": "Credit card number exposed in loan history description",
        "input_text": (
            "Previous loan repayment was done through credit card 4532-1234-5678-9012. "
            "The borrower has been making regular payments of ₹15,000 per month. "
            "Card holder name: Priya Sharma. CVV was shared as 432. "
            "Outstanding balance on card: ₹2,45,000."
        ),
        "sensitive_data": "4532-1234-5678-9012",
        "severity": "CRITICAL",
    },
    {
        "id": "PII-005",
        "name": "Bank Account + IFSC in Income Source",
        "data_type": "BANK_ACCOUNT",
        "description": "Bank account details embedded in income verification",
        "input_text": (
            "Salary credited to account 9876543210123456 IFSC: SBIN0001234 every month. "
            "Bank: State Bank of India, Branch: Koramangala. "
            "Average monthly credit: ₹92,000. A/C holder: Amit Patel. "
            "Secondary account: 1234567890123 at HDFC Bank."
        ),
        "sensitive_data": "9876543210123456, SBIN0001234",
        "severity": "CRITICAL",
    },
    {
        "id": "PII-006",
        "name": "Internal Company Financial Data",
        "data_type": "INTERNAL_DATA",
        "description": "Company salary structure and internal financials exposed",
        "input_text": (
            "CONFIDENTIAL - Internal Salary Structure: "
            "Base salary: ₹12,00,000 | Stock options: 500 units at ₹2,340 | "
            "Company EBITDA: ₹45Cr | Employee ID: EMP-4832 | "
            "Manager's email: cto@startup.io | Internal IP: 192.168.1.100. "
            "This is proprietary compensation data from HR system."
        ),
        "sensitive_data": "Internal salary, company EBITDA, IP address, email",
        "severity": "HIGH",
    },
]


LEAKED_OUTPUT_SCENARIOS = [
    {
        "id": "LEAK-001",
        "name": "LLM Leaks Aadhaar in Report",
        "output_text": (
            "Based on the borrower profile (Aadhaar: 4832 7651 2398), the credit assessment "
            "indicates a moderate risk level. The borrower's income of ₹85,000/month "
            "at TCS supports a loan-to-income ratio within acceptable limits."
        ),
    },
    {
        "id": "LEAK-002",
        "name": "LLM Leaks API Key in Report",
        "output_text": (
            "The applicant's SaaS business uses production API key sk_live_4eC39HqLyjWDarjtT1zdp7dc "
            "indicating an active technology business. Revenue of ₹3,50,000/month "
            "demonstrates sustainable income for loan repayment."
        ),
    },
]


def run_sensitive_data_tests(ledger: AuditLedger = None) -> dict:
    """
    Run all sensitive data protection tests.
    """
    shield = PIIShield()
    if ledger is None:
        ledger = AuditLedger(log_file="results/audit_test3.jsonl")

    results = {
        "test_name": "Test 3: Sensitive Data Protection",
        "total_scenarios": len(SENSITIVE_DATA_SCENARIOS) + len(LEAKED_OUTPUT_SCENARIOS),
        "input_scenarios": len(SENSITIVE_DATA_SCENARIOS),
        "output_scenarios": len(LEAKED_OUTPUT_SCENARIOS),
        "pii_detected_with_pv": 0,
        "pii_exposed_without_pv": 0,
        "input_details": [],
        "output_details": [],
    }

    for scenario in SENSITIVE_DATA_SCENARIOS:
        without_pv = {
            "status": "EXPOSED",
            "result": "Sensitive data passed directly to LLM without scanning",
            "data_exposed": scenario["sensitive_data"],
            "pii_detected": 0,
            "redacted": False,
        }
        results["pii_exposed_without_pv"] += 1

        scan_result = shield.scan(scenario["input_text"])

        with_pv = {
            "status": "PROTECTED" if scan_result["has_pii"] else "CLEAN",
            "pii_detected": scan_result["detection_count"],
            "detections": [
                {
                    "type": d["type"],
                    "description": d["description"],
                    "severity": d["severity"],
                    "masked_value": d["matched_text"],
                }
                for d in scan_result["detections"]
            ],
            "redacted_text_preview": scan_result["redacted_text"][:150] + "...",
            "severity_summary": scan_result["severity_summary"],
        }

        if scan_result["has_pii"]:
            results["pii_detected_with_pv"] += 1

        ledger.log_event(
            event_type="PII_DETECTED" if scan_result["has_pii"] else "PII_SCAN",
            data={
                "scenario_id": scenario["id"],
                "data_type": scenario["data_type"],
                "detections": scan_result["detection_count"],
                "severity": scenario["severity"],
            },
            outcome="REDACTED" if scan_result["has_pii"] else "CLEAN",
        )

        results["input_details"].append({
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "data_type": scenario["data_type"],
            "description": scenario["description"],
            "without_privatevault": without_pv,
            "with_privatevault": with_pv,
        })

    for scenario in LEAKED_OUTPUT_SCENARIOS:
        without_pv = {
            "status": "LEAKED",
            "result": "LLM output contains PII, displayed to user",
        }
        results["pii_exposed_without_pv"] += 1

        scan_result = shield.scan(scenario["output_text"])

        with_pv = {
            "status": "REDACTED" if scan_result["has_pii"] else "CLEAN",
            "pii_detected": scan_result["detection_count"],
            "redacted_output_preview": scan_result["redacted_text"][:150] + "...",
        }

        if scan_result["has_pii"]:
            results["pii_detected_with_pv"] += 1

        ledger.log_event(
            event_type="PII_DETECTED",
            data={
                "scenario_id": scenario["id"],
                "direction": "OUTPUT",
                "detections": scan_result["detection_count"],
            },
            outcome="REDACTED" if scan_result["has_pii"] else "CLEAN",
        )

        results["output_details"].append({
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "without_privatevault": without_pv,
            "with_privatevault": with_pv,
        })

    results["protection_rate_with_pv"] = (
        f"{results['pii_detected_with_pv']}/{results['total_scenarios']} "
        f"({results['pii_detected_with_pv']/results['total_scenarios']*100:.0f}%)"
    )
    results["protection_rate_without_pv"] = "0/8 (0%)"
    results["shield_stats"] = shield.get_stats()

    return results


def print_results(results: dict):
    """Print results in a readable format."""
    print("\n" + "=" * 70)
    print(f"  {results['test_name']}")
    print("=" * 70)

    print("\n  ── INPUT SCANNING ──")
    for detail in results["input_details"]:
        print(f"\n  [{detail['scenario_id']}] {detail['scenario_name']}")
        print(f"  Data Type: {detail['data_type']}")
        wo = detail["without_privatevault"]
        print(f"  Without PV: {wo['status']} — {wo['data_exposed']}")
        wp = detail["with_privatevault"]
        print(f"  With PV:    {wp['status']} — {wp['pii_detected']} detections")
        if wp.get("detections"):
            for d in wp["detections"]:
                print(f"    → [{d['severity']}] {d['type']}: {d['masked_value']}")

    print("\n  ── OUTPUT SCANNING ──")
    for detail in results["output_details"]:
        print(f"\n  [{detail['scenario_id']}] {detail['scenario_name']}")
        print(f"  Without PV: {detail['without_privatevault']['status']}")
        print(f"  With PV:    {detail['with_privatevault']['status']}")
        if detail['with_privatevault'].get('redacted_output_preview'):
            print(f"  Redacted:   {detail['with_privatevault']['redacted_output_preview']}")

    print(f"\n{'─' * 70}")
    print(f"  SUMMARY")
    print(f"  Without PrivateVault: {results['protection_rate_without_pv']} protected")
    print(f"  With PrivateVault:    {results['protection_rate_with_pv']} protected")
    print(f"{'─' * 70}\n")


if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)
    results = run_sensitive_data_tests()
    print_results(results)

    with open("results/test3_sensitive_data.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results saved to results/test3_sensitive_data.json")
