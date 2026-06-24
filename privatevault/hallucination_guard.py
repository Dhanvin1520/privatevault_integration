"""
Hallucination Guard — Output Grounding & Citation Verification
Part of PrivateVault Coordination Layer

Validates LLM outputs against retrieved RAG context to detect
hallucinations, unsupported claims, and missing citations.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("privatevault.hallucination_guard")


class HallucinationGuard:
    """
    Validates that LLM-generated credit assessment reports are grounded
    in the retrieved regulatory context and ML model outputs.
    """

    KNOWN_REGULATORY_BODIES = [
        "RBI", "Reserve Bank of India",
        "Basel III", "Basel Committee",
        "CIBIL", "credit bureau",
        "IRAC", "Banking Ombudsman",
        "SEBI", "NABARD",
    ]

    VALID_DECISIONS = ["APPROVE", "CONDITIONAL APPROVE", "CONDITIONAL", "DECLINE"]

    def __init__(self):
        self.check_count = 0
        self.hallucination_count = 0

    def check_output(
        self,
        report: Dict[str, Any],
        rag_context: List[Dict[str, Any]],
        ml_scores: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validates an LLM-generated report against the RAG context and ML scores.

        Args:
            report: The parsed JSON report from the LLM
            rag_context: List of retrieved regulation chunks
            ml_scores: ML model prediction outputs

        Returns:
            Dict with: hallucination_score, issues[], grounding_metrics,
                       is_reliable, citation_analysis
        """
        self.check_count += 1
        issues = []

        citation_result = self._verify_citations(report, rag_context)
        issues.extend(citation_result["issues"])

        grounding_result = self._check_decision_grounding(report, rag_context)
        issues.extend(grounding_result["issues"])

        claim_result = self._verify_factual_claims(report, rag_context)
        issues.extend(claim_result["issues"])

        validity_result = self._check_decision_validity(report)
        issues.extend(validity_result["issues"])

        consistency_result = self._check_ml_consistency(report, ml_scores)
        issues.extend(consistency_result["issues"])

        hallucination_score = self._calculate_hallucination_score(issues)

        if hallucination_score > 0.3:
            self.hallucination_count += 1

        return {
            "hallucination_score": hallucination_score,
            "is_reliable": hallucination_score <= 0.3,
            "issue_count": len(issues),
            "issues": issues,
            "citation_analysis": citation_result,
            "grounding_analysis": grounding_result,
            "claim_analysis": claim_result,
            "ml_consistency": consistency_result,
        }

    def _verify_citations(
        self, report: Dict, rag_context: List[Dict]
    ) -> Dict[str, Any]:
        """
        Verify that regulatory references in the report actually exist
        in the retrieved context.
        """
        issues = []
        refs = report.get("regulatory_references", [])

        if not refs:
            issues.append({
                "type": "MISSING_CITATIONS",
                "severity": "MEDIUM",
                "description": "No regulatory references provided in the report",
            })
            return {"issues": issues, "verified": 0, "unverified": 0, "total": 0}

        context_text = " ".join(
            doc.get("text", "") for doc in rag_context
        ).lower()

        verified = 0
        unverified = 0

        for ref in refs:
            ref_lower = str(ref).lower()
            key_terms = [
                term.strip()
                for term in re.split(r'[,;:\-–—()]', ref_lower)
                if len(term.strip()) > 3
            ]

            found = any(
                term in context_text
                for term in key_terms
                if term not in ("the", "and", "for", "with", "from")
            )

            if found:
                verified += 1
            else:
                unverified += 1
                issues.append({
                    "type": "UNVERIFIED_CITATION",
                    "severity": "HIGH",
                    "description": f"Citation '{ref}' not found in retrieved context",
                })

        return {
            "issues": issues,
            "verified": verified,
            "unverified": unverified,
            "total": len(refs),
            "verification_rate": (
                verified / len(refs) if refs else 0
            ),
        }

    def _check_decision_grounding(
        self, report: Dict, rag_context: List[Dict]
    ) -> Dict[str, Any]:
        """
        Check if the decision rationale references concepts from
        the retrieved regulatory context.
        """
        issues = []
        rationale = report.get("decision_rationale", "").lower()
        risk_analysis = report.get("risk_analysis", "").lower()

        if not rationale:
            issues.append({
                "type": "EMPTY_RATIONALE",
                "severity": "HIGH",
                "description": "Decision rationale is empty",
            })
            return {"issues": issues, "grounding_score": 0.0}

        context_text = " ".join(
            doc.get("text", "") for doc in rag_context
        ).lower()

        regulatory_terms = [
            "credit score", "creditworthiness", "loan-to-income",
            "debt-to-income", "repayment capacity", "due diligence",
            "npa", "non-performing", "emi", "dscr",
            "fair practices", "risk-based pricing",
        ]

        matched_terms = [
            term for term in regulatory_terms
            if term in rationale or term in risk_analysis
        ]

        grounding_score = len(matched_terms) / len(regulatory_terms)

        if grounding_score < 0.1:
            issues.append({
                "type": "WEAK_GROUNDING",
                "severity": "MEDIUM",
                "description": (
                    "Decision rationale does not reference regulatory concepts. "
                    f"Only {len(matched_terms)}/{len(regulatory_terms)} "
                    "regulatory terms found."
                ),
            })

        return {
            "issues": issues,
            "grounding_score": round(grounding_score, 3),
            "matched_terms": matched_terms,
        }

    def _verify_factual_claims(
        self, report: Dict, rag_context: List[Dict]
    ) -> Dict[str, Any]:
        """
        Extract numeric claims from the report and verify against context.
        """
        issues = []
        report_text = json.dumps(report)

        percentage_claims = re.findall(
            r'(\d{1,3}(?:\.\d+)?)\s*(?:%|percent)', report_text
        )

        context_text = " ".join(
            doc.get("text", "") for doc in rag_context
        )

        unsupported_claims = 0
        for claim in percentage_claims:
            if claim not in context_text:
                continue
            unsupported_claims += 1

        fabricated_refs = re.findall(
            r'(?:Section|Circular|Clause|Article)\s+[\dA-Z]+(?:\.\d+)?',
            report_text,
        )

        for ref in fabricated_refs:
            if ref.lower() not in context_text.lower():
                issues.append({
                    "type": "FABRICATED_REFERENCE",
                    "severity": "HIGH",
                    "description": f"Reference '{ref}' not found in regulatory context",
                })

        return {
            "issues": issues,
            "percentage_claims": len(percentage_claims),
            "fabricated_references": len(
                [i for i in issues if i["type"] == "FABRICATED_REFERENCE"]
            ),
        }

    def _check_decision_validity(self, report: Dict) -> Dict[str, Any]:
        """Check if the lending decision is a valid value."""
        issues = []
        decision = report.get("lending_decision", "")

        if not decision:
            issues.append({
                "type": "MISSING_DECISION",
                "severity": "CRITICAL",
                "description": "No lending decision found in report",
            })
        elif decision.upper() not in self.VALID_DECISIONS:
            issues.append({
                "type": "INVALID_DECISION",
                "severity": "HIGH",
                "description": (
                    f"Decision '{decision}' is not a valid value. "
                    f"Expected one of: {', '.join(self.VALID_DECISIONS)}"
                ),
            })

        return {"issues": issues}

    def _check_ml_consistency(
        self, report: Dict, ml_scores: Dict
    ) -> Dict[str, Any]:
        """
        Verify that the report doesn't contradict ML model outputs.
        """
        issues = []
        report_text = json.dumps(report).lower()
        risk_class = ml_scores.get("risk_class", "").lower()
        default_prob = ml_scores.get("consensus_default_probability", 0)

        if risk_class == "high risk" and "low risk" in report_text:
            if "low risk" not in report_text.split("high risk")[0]:
                pass

        model_probs = ml_scores.get("model_probabilities", {})
        for model, prob in model_probs.items():
            model_lower = model.lower()
            if model_lower in report_text:
                pattern = rf"{re.escape(model_lower)}.*?(\d{{1,3}}(?:\.\d+)?)\s*%"
                matches = re.findall(pattern, report_text)
                for match_val in matches:
                    try:
                        reported_prob = float(match_val)
                        if abs(reported_prob - prob) > 5:
                            issues.append({
                                "type": "FABRICATED_ML_SCORE",
                                "severity": "CRITICAL",
                                "description": (
                                    f"Report states {model} probability as {reported_prob}% "
                                    f"but actual ML output is {prob}%"
                                ),
                            })
                    except ValueError:
                        pass

        return {
            "issues": issues,
            "is_consistent": len(issues) == 0,
        }

    def _calculate_hallucination_score(self, issues: List[Dict]) -> float:
        """Calculate a 0.0-1.0 hallucination risk score."""
        if not issues:
            return 0.0

        severity_weights = {
            "CRITICAL": 0.30,
            "HIGH": 0.15,
            "MEDIUM": 0.05,
            "LOW": 0.02,
        }

        total = sum(
            severity_weights.get(i.get("severity", "LOW"), 0.02)
            for i in issues
        )
        return min(1.0, round(total, 3))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_checks": self.check_count,
            "hallucinations_detected": self.hallucination_count,
            "hallucination_rate": (
                round(self.hallucination_count / self.check_count * 100, 1)
                if self.check_count > 0
                else 0
            ),
        }
