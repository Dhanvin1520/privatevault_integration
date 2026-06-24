"""
PII Shield — Sensitive Data Detection & Redaction
Part of PrivateVault Coordination Layer

Detects and redacts PII (Personally Identifiable Information) and
sensitive financial data in both inputs and outputs of the AI pipeline.
"""

import re
import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger("privatevault.pii_shield")


class PIIShield:
    """
    Bidirectional PII scanner that detects and redacts sensitive data
    before it reaches the LLM or is exposed in outputs.

    Covers Indian-specific identifiers (Aadhaar, PAN), financial data,
    API keys, and common PII patterns.
    """


    PII_PATTERNS = {
        "AADHAAR": {
            "pattern": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
            "description": "Aadhaar Number (12-digit Indian ID)",
            "severity": "CRITICAL",
            "redaction": "[AADHAAR_REDACTED]",
        },
        "PAN_CARD": {
            "pattern": r"\b[A-Z]{5}\d{4}[A-Z]\b",
            "description": "PAN Card Number (Indian tax ID)",
            "severity": "CRITICAL",
            "redaction": "[PAN_REDACTED]",
        },
        "CREDIT_CARD": {
            "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "description": "Credit/Debit Card Number",
            "severity": "CRITICAL",
            "redaction": "[CARD_REDACTED]",
        },
        "API_KEY": {
            "pattern": r"(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,})['\"]?",
            "description": "API Key or Secret Token",
            "severity": "CRITICAL",
            "redaction": "[API_KEY_REDACTED]",
        },
        "API_KEY_FORMAT": {
            "pattern": r"\b(?:sk|pk|gsk|xai|ghp|glpat|AKIA|sk_live|sk_test|pk_live|pk_test)[_\-]?[A-Za-z0-9]{10,}\b",
            "description": "API Key (format-based detection)",
            "severity": "CRITICAL",
            "redaction": "[API_KEY_REDACTED]",
        },
        "EMAIL": {
            "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "description": "Email Address",
            "severity": "HIGH",
            "redaction": "[EMAIL_REDACTED]",
        },
        "PHONE_INDIA": {
            "pattern": r"\b(?:\+91[-\s]?)?[6-9]\d{4}[-\s]?\d{5}\b",
            "description": "Indian Phone Number",
            "severity": "HIGH",
            "redaction": "[PHONE_REDACTED]",
        },
        "PHONE_INTERNATIONAL": {
            "pattern": r"\b\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b",
            "description": "International Phone Number",
            "severity": "MEDIUM",
            "redaction": "[PHONE_REDACTED]",
        },
        "BANK_ACCOUNT": {
            "pattern": r"\b\d{9,18}\b(?=.*(?:IFSC|account|A/C|a/c))",
            "description": "Bank Account Number",
            "severity": "CRITICAL",
            "redaction": "[BANK_ACCOUNT_REDACTED]",
        },
        "IFSC_CODE": {
            "pattern": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
            "description": "IFSC Code (Indian bank branch)",
            "severity": "HIGH",
            "redaction": "[IFSC_REDACTED]",
        },
        "SSN": {
            "pattern": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
            "description": "SSN-like Pattern",
            "severity": "CRITICAL",
            "redaction": "[SSN_REDACTED]",
        },
        "IP_ADDRESS": {
            "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "description": "IP Address",
            "severity": "MEDIUM",
            "redaction": "[IP_REDACTED]",
        },
        "AWS_KEY": {
            "pattern": r"\bAKIA[0-9A-Z]{16}\b",
            "description": "AWS Access Key ID",
            "severity": "CRITICAL",
            "redaction": "[AWS_KEY_REDACTED]",
        },
    }


    FINANCIAL_PATTERNS = {
        "SALARY_DETAILS": {
            "pattern": r"(?:salary|CTC|compensation|take[\s-]?home)\s*[:=]?\s*(?:₹|Rs\.?|INR)?\s*[\d,]+",
            "description": "Salary/Compensation Details",
            "severity": "HIGH",
            "redaction": "[SALARY_REDACTED]",
        },
        "INTERNAL_DATA": {
            "pattern": r"(?:internal|confidential|proprietary|trade\s*secret)",
            "description": "Internal/Confidential Data Marker",
            "severity": "MEDIUM",
            "redaction": None,
        },
    }

    def __init__(self, redaction_mode: str = "full"):
        """
        Args:
            redaction_mode: 'full' replaces with [TYPE_REDACTED],
                          'partial' masks middle characters (e.g., XXXX-XXXX-1234)
        """
        self.redaction_mode = redaction_mode
        self.detections: List[Dict[str, Any]] = []
        self.scan_count = 0

    def scan(self, text: str) -> Dict[str, Any]:
        """
        Scans text for all PII and sensitive data patterns.

        Returns:
            Dict with: has_pii, detections[], redacted_text, detection_count
        """
        self.scan_count += 1
        detections = []

        for pii_type, config in self.PII_PATTERNS.items():
            matches = re.finditer(config["pattern"], text, re.IGNORECASE)
            for match in matches:
                detections.append({
                    "type": pii_type,
                    "description": config["description"],
                    "severity": config["severity"],
                    "matched_text": self._partial_mask(match.group()),
                    "position": match.span(),
                    "redaction_label": config["redaction"],
                })

        for fin_type, config in self.FINANCIAL_PATTERNS.items():
            matches = re.finditer(config["pattern"], text, re.IGNORECASE)
            for match in matches:
                detections.append({
                    "type": fin_type,
                    "description": config["description"],
                    "severity": config["severity"],
                    "matched_text": self._partial_mask(match.group()),
                    "position": match.span(),
                    "redaction_label": config.get("redaction"),
                })

        detections = self._deduplicate(detections)
        self.detections.extend(detections)

        has_pii = len(detections) > 0
        redacted_text = self.redact(text) if has_pii else text

        return {
            "has_pii": has_pii,
            "detections": detections,
            "detection_count": len(detections),
            "redacted_text": redacted_text,
            "severity_summary": self._severity_summary(detections),
        }

    def redact(self, text: str) -> str:
        """
        Applies redaction to all detected PII patterns in text.
        """
        redacted = text

        for pii_type, config in self.PII_PATTERNS.items():
            if config["redaction"]:
                redacted = re.sub(
                    config["pattern"],
                    config["redaction"],
                    redacted,
                    flags=re.IGNORECASE,
                )

        for fin_type, config in self.FINANCIAL_PATTERNS.items():
            if config.get("redaction"):
                redacted = re.sub(
                    config["pattern"],
                    config["redaction"],
                    redacted,
                    flags=re.IGNORECASE,
                )

        return redacted

    def _partial_mask(self, text: str) -> str:
        """Show first 2 and last 2 characters, mask the rest."""
        if len(text) <= 4:
            return "****"
        return text[:2] + "*" * (len(text) - 4) + text[-2:]

    def _deduplicate(self, detections: List[Dict]) -> List[Dict]:
        """Remove duplicate detections at overlapping positions."""
        seen = set()
        unique = []
        for d in detections:
            key = (d["type"], d["position"])
            if key not in seen:
                seen.add(key)
                unique.append(d)
        return unique

    def _severity_summary(self, detections: List[Dict]) -> Dict[str, int]:
        """Count detections by severity level."""
        summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for d in detections:
            sev = d.get("severity", "LOW")
            summary[sev] = summary.get(sev, 0) + 1
        return summary

    def get_stats(self) -> Dict[str, Any]:
        """Return PII shield statistics."""
        return {
            "total_scans": self.scan_count,
            "total_detections": len(self.detections),
            "by_type": self._count_by_type(),
        }

    def _count_by_type(self) -> Dict[str, int]:
        counts = {}
        for d in self.detections:
            t = d["type"]
            counts[t] = counts.get(t, 0) + 1
        return counts
