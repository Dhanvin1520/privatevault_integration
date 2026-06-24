"""
Lending Policy Engine — Runtime Policy Enforcement
Adapted from PrivateVault.ai's policy_engine.py

Validates LLM outputs against RBI regulations and business rules
before they are presented to the user. Ensures decision consistency
between ML models and LLM-generated recommendations.
"""

import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("privatevault.policy_engine")


class LendingPolicyEngine:
    """
    Runtime policy enforcement layer that validates AI lending decisions
    against regulatory requirements (RBI, Basel III) and internal business rules.

    Adapted from PrivateVault's policy engine:
    https://github.com/LOLA0786/PrivateVault.ai/blob/main/policy_engine.py
    """

    PROTECTED_ATTRIBUTES = [
        "gender", "religion", "caste", "ethnicity", "race",
        "place of origin", "nationality", "marital status",
        "sexual orientation", "disability", "political affiliation",
    ]

    POLICY_RULES = {
        "min_credit_score_for_approval": 300,
        "high_risk_credit_score_threshold": 650,
        "max_emi_to_income_ratio": 0.50,
        "min_dscr_commercial": 1.25,
        "npa_days_threshold": 90,
        "max_approval_probability_for_decline": 0.40,
        "min_decline_probability_for_approve": 0.20,
    }

    def __init__(self, custom_rules: Dict[str, Any] = None):
        self.rules = {**self.POLICY_RULES, **(custom_rules or {})}
        self.violations: List[Dict[str, Any]] = []
        self.check_count = 0

    def validate_decision(
        self,
        report: Dict[str, Any],
        ml_scores: Dict[str, Any],
        borrower_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validates the LLM-generated lending decision against policy rules.

        Args:
            report: The LLM assessment report (JSON)
            ml_scores: ML model predictions
            borrower_profile: Original borrower data

        Returns:
            Dict with: is_compliant, violations[], corrected_decision (if any)
        """
        self.check_count += 1
        violations = []

        v = self._check_decision_consistency(report, ml_scores)
        if v:
            violations.append(v)

        v_list = self._check_protected_attributes(report)
        violations.extend(v_list)

        v = self._check_credit_score_policy(report, borrower_profile)
        if v:
            violations.append(v)

        v = self._check_emi_ratio(borrower_profile)
        if v:
            violations.append(v)

        v = self._check_default_history(report, borrower_profile)
        if v:
            violations.append(v)

        v_list = self._check_required_fields(report)
        violations.extend(v_list)

        self.violations.extend(violations)

        is_compliant = len(violations) == 0
        corrected = None
        if not is_compliant:
            corrected = self._suggest_correction(report, violations, ml_scores)

        return {
            "is_compliant": is_compliant,
            "violations": violations,
            "violation_count": len(violations),
            "corrected_decision": corrected,
            "policy_rules_checked": 6,
        }

    def _check_decision_consistency(
        self, report: Dict, ml_scores: Dict
    ) -> Optional[Dict]:
        """
        Ensure LLM decision aligns with ML risk score.
        Cannot APPROVE a 90% default probability. Cannot DECLINE a 5%.
        """
        decision = report.get("lending_decision", "").upper()
        default_prob = ml_scores.get("consensus_default_probability", 0) / 100

        if decision == "APPROVE" and default_prob > self.rules["max_approval_probability_for_decline"]:
            return {
                "rule": "DECISION_SCORE_CONSISTENCY",
                "severity": "CRITICAL",
                "description": (
                    f"LLM approved loan but ML default probability is "
                    f"{default_prob*100:.1f}% (threshold: "
                    f"{self.rules['max_approval_probability_for_decline']*100}%). "
                    f"Decision contradicts quantitative risk assessment."
                ),
                "recommended_action": "Change to DECLINE or CONDITIONAL APPROVE",
            }

        if decision == "DECLINE" and default_prob < self.rules["min_decline_probability_for_approve"]:
            return {
                "rule": "DECISION_SCORE_CONSISTENCY",
                "severity": "HIGH",
                "description": (
                    f"LLM declined loan but ML default probability is only "
                    f"{default_prob*100:.1f}% (threshold: "
                    f"{self.rules['min_decline_probability_for_approve']*100}%). "
                    f"Low-risk borrower should not be declined without cause."
                ),
                "recommended_action": "Change to APPROVE or CONDITIONAL APPROVE",
            }

        return None

    def _check_protected_attributes(self, report: Dict) -> List[Dict]:
        """Check if the report references protected attributes in decision-making."""
        violations = []
        report_text = str(report).lower()

        for attr in self.PROTECTED_ATTRIBUTES:
            patterns = [
                rf"(?:due to|because of|based on|considering)\s+(?:the\s+)?(?:borrower'?s?\s+)?{attr}",
                rf"{attr}\s+(?:is|was|indicates|suggests|affects)",
                rf"(?:the\s+)?{attr}\s+of\s+the\s+borrower",
            ]
            for pattern in patterns:
                if re.search(pattern, report_text, re.IGNORECASE):
                    violations.append({
                        "rule": "PROTECTED_ATTRIBUTE_BIAS",
                        "severity": "CRITICAL",
                        "description": (
                            f"Decision references protected attribute '{attr}'. "
                            f"RBI non-discrimination principles prohibit decisions "
                            f"based on {attr}."
                        ),
                        "recommended_action": f"Remove reference to '{attr}' from decision rationale",
                    })
                    break

        return violations

    def _check_credit_score_policy(
        self, report: Dict, profile: Dict
    ) -> Optional[Dict]:
        """Validate credit score against RBI thresholds."""
        credit_score = profile.get("credit_score", 0)
        decision = report.get("lending_decision", "").upper()

        if credit_score < self.rules["high_risk_credit_score_threshold"] and decision == "APPROVE":
            return {
                "rule": "CREDIT_SCORE_THRESHOLD",
                "severity": "HIGH",
                "description": (
                    f"Credit score {credit_score} is below high-risk threshold "
                    f"({self.rules['high_risk_credit_score_threshold']}). "
                    f"RBI requires enhanced due diligence for such borrowers. "
                    f"Outright approval without conditions violates policy."
                ),
                "recommended_action": "Add conditions or change to CONDITIONAL APPROVE",
            }
        return None

    def _check_emi_ratio(self, profile: Dict) -> Optional[Dict]:
        """Check EMI-to-Income ratio against RBI guidelines."""
        income = profile.get("income", 1)
        loan_amount = profile.get("loan_amount", 0)
        interest_rate = profile.get("interest_rate", 10.0) / 100

        monthly_income = income / 12
        estimated_emi = (loan_amount * (1 + interest_rate)) / 12

        if monthly_income > 0:
            ratio = estimated_emi / monthly_income
            if ratio > self.rules["max_emi_to_income_ratio"]:
                return {
                    "rule": "EMI_INCOME_RATIO",
                    "severity": "HIGH",
                    "description": (
                        f"Estimated EMI-to-income ratio is {ratio:.2f} "
                        f"({ratio*100:.0f}%), exceeding RBI guideline of "
                        f"{self.rules['max_emi_to_income_ratio']*100:.0f}%. "
                        f"Borrower may be over-indebted."
                    ),
                    "recommended_action": "Reduce loan amount or require additional income proof",
                }
        return None

    def _check_default_history(
        self, report: Dict, profile: Dict
    ) -> Optional[Dict]:
        """Ensure previous defaults are properly addressed."""
        prev_defaults = str(profile.get("previous_defaults", "No")).lower()
        decision = report.get("lending_decision", "").upper()
        rationale = report.get("decision_rationale", "").lower()

        if prev_defaults == "yes" and decision == "APPROVE":
            if "default" not in rationale and "previous" not in rationale:
                return {
                    "rule": "DEFAULT_HISTORY_ACKNOWLEDGMENT",
                    "severity": "HIGH",
                    "description": (
                        "Borrower has previous defaults on file but the approval "
                        "decision does not acknowledge or address this risk factor. "
                        "RBI requires enhanced due diligence for such cases."
                    ),
                    "recommended_action": "Add conditions addressing default history",
                }
        return None

    def _check_required_fields(self, report: Dict) -> List[Dict]:
        """Ensure all mandatory report fields are present."""
        required = [
            "borrower_summary",
            "risk_analysis",
            "lending_decision",
            "decision_rationale",
            "disclaimer",
        ]
        violations = []
        for field in required:
            if field not in report or not report[field]:
                violations.append({
                    "rule": "REQUIRED_FIELD_MISSING",
                    "severity": "MEDIUM",
                    "description": f"Required report field '{field}' is missing or empty.",
                    "recommended_action": f"Populate the '{field}' field",
                })
        return violations

    def _suggest_correction(
        self, report: Dict, violations: List[Dict], ml_scores: Dict
    ) -> Optional[str]:
        """Suggest a corrected decision based on violations and ML scores."""
        default_prob = ml_scores.get("consensus_default_probability", 50)

        if default_prob >= 60:
            return "DECLINE"
        elif default_prob >= 30:
            return "CONDITIONAL APPROVE"
        else:
            return "APPROVE"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_checks": self.check_count,
            "total_violations": len(self.violations),
            "by_rule": self._count_by_rule(),
        }

    def _count_by_rule(self) -> Dict[str, int]:
        counts = {}
        for v in self.violations:
            r = v["rule"]
            counts[r] = counts.get(r, 0) + 1
        return counts
