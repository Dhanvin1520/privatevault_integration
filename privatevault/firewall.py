"""
AI Firewall — Bidirectional Input/Output Filtering
Adapted from PrivateVault.ai's ai_firewall_core.py

Detects prompt injection, jailbreak attempts, and malicious input patterns
before they reach the LLM inference layer.
"""

import re
import base64
import logging
from typing import Tuple, List, Dict, Any

logger = logging.getLogger("privatevault.firewall")


class AIFirewall:
    """
    Runtime input protection layer that scans all prompts and user inputs
    for injection attacks, jailbreak patterns, and encoded evasion attempts.

    Adapted from PrivateVault's AIFirewall class:
    https://github.com/LOLA0786/PrivateVault.ai/blob/main/ai_firewall_core.py
    """

    INJECTION_PATTERNS = [
        r"ignore\s+(previous|all|above)\s+instructions?",
        r"disregard\s+(previous|safety|all)\s+(instructions?|guidelines?)",
        r"you\s+are\s+now\s+(in\s+)?(developer|admin|god)\s+mode",
        r"system\s*:\s*new\s+instructions?",
        r"<\|im_start\|>",
        r"ENDPOINT\s+OVERRIDE",
        r"sudo\s+mode\s+activated",
        r"forget\s+(everything|all)\s+you\s+know",
        r"\[SYSTEM\]\s*:",
        r"role\s*=\s*['\"]system['\"]",
        r"override\s+(all\s+)?polic(y|ies)",
        r"new\s+system\s+prompt",
        r"reveal\s+(your\s+)?(system|hidden)\s+prompt",
        r"output\s+(your\s+)?complete\s+system\s+prompt",
        r"show\s+(me\s+)?(your\s+)?instructions",
        r"what\s+are\s+your\s+(system\s+)?instructions",
    ]

    JAILBREAK_PATTERNS = [
        r"(DAN|DUDE|STAN)\s+mode",
        r"you\s+are\s+unrestricted",
        r"no\s+ethical\s+guidelines",
        r"bypass\s+(safety|filters?|restrictions?)",
        r"act\s+as\s+if\s+you\s+have\s+no\s+limitations",
        r"pretend\s+you\s+(can|are)",
        r"hypothetically\s+if\s+you\s+could",
        r"you\s+are\s+now\s+free\s+from",
        r"ignore\s+(safety|ethical)\s+(constraints|rules)",
        r"respond\s+without\s+(any\s+)?restrictions",
    ]

    DOMAIN_ATTACK_PATTERNS = [
        r"approve\s+(this\s+)?loan\s+unconditionally",
        r"regardless\s+of\s+risk",
        r"treat\s+as\s+(no|zero)\s+risk",
        r"system\s+error.*treat\s+as",
        r"ignore\s+this.*default",
        r"override\s+risk\s+classification",
        r"lending_decision\s*[\"']?\s*:\s*[\"']?\s*APPROVE",
        r"force\s+approv(e|al)",
        r"return\s+the\s+response\s+in\s+(exactly\s+)?this\s+format",
        r"with\s+no\s+changes.*lending_decision",
        r"this\s+is\s+a\s+test\s+override",
    ]

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            "input_protection": {"enabled": True, "sensitivity": "high"},
            "output_protection": {"enabled": True},
            "logging": {"enabled": True},
        }
        self.blocked_count = 0
        self.scan_count = 0

    def scan_input(self, text: str) -> Dict[str, Any]:
        """
        Scans user input for prompt injection, jailbreak, and domain attacks.

        Returns:
            Dict with keys: is_safe, threats[], risk_score, sanitized_text
        """
        self.scan_count += 1
        threats = []
        text_lower = text.lower()

        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                threats.append({
                    "type": "PROMPT_INJECTION",
                    "pattern": pattern,
                    "severity": "CRITICAL",
                    "description": f"Prompt injection detected matching: {pattern}",
                })

        for pattern in self.JAILBREAK_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                threats.append({
                    "type": "JAILBREAK_ATTEMPT",
                    "pattern": pattern,
                    "severity": "CRITICAL",
                    "description": f"Jailbreak attempt detected matching: {pattern}",
                })

        for pattern in self.DOMAIN_ATTACK_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                threats.append({
                    "type": "DOMAIN_ATTACK",
                    "pattern": pattern,
                    "severity": "HIGH",
                    "description": f"Domain-specific attack detected: {pattern}",
                })

        b64_result = self._check_base64_injection(text)
        if b64_result:
            threats.append({
                "type": "ENCODED_INJECTION",
                "pattern": "base64",
                "severity": "CRITICAL",
                "description": f"Base64-encoded malicious content: {b64_result}",
            })

        risk_score = self._calculate_risk_score(threats)
        is_safe = len(threats) == 0

        if not is_safe:
            self.blocked_count += 1

        return {
            "is_safe": is_safe,
            "threats": threats,
            "risk_score": risk_score,
            "threat_count": len(threats),
            "sanitized_text": self._sanitize(text) if not is_safe else text,
        }

    def scan_output(self, text: str) -> Dict[str, Any]:
        """
        Scans LLM output for leaked system prompts or injection artifacts.
        """
        threats = []
        text_lower = text.lower()

        system_leak_patterns = [
            r"MANDATORY\s+RULES",
            r"system\s+prompt\s*:",
            r"my\s+instructions\s+are",
            r"I\s+was\s+instructed\s+to",
            r"here\s+are\s+my\s+(system\s+)?instructions",
        ]

        for pattern in system_leak_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                threats.append({
                    "type": "SYSTEM_PROMPT_LEAK",
                    "pattern": pattern,
                    "severity": "CRITICAL",
                })

        return {
            "is_safe": len(threats) == 0,
            "threats": threats,
            "risk_score": 1.0 if threats else 0.0,
        }

    def _check_base64_injection(self, text: str) -> str:
        """Detect base64 encoded prompt injections."""
        b64_pattern = r'[A-Za-z0-9+/]{16,}={0,2}'
        matches = re.findall(b64_pattern, text)

        all_patterns = (
            self.INJECTION_PATTERNS
            + self.JAILBREAK_PATTERNS
            + self.DOMAIN_ATTACK_PATTERNS
        )

        for match in matches:
            try:
                padded = match + '=' * (4 - len(match) % 4) if len(match) % 4 else match
                decoded = base64.b64decode(padded).decode('utf-8', errors='ignore').lower()
                for pattern in all_patterns:
                    if re.search(pattern, decoded, re.IGNORECASE):
                        return decoded[:100]
                injection_keywords = [
                    'ignore', 'override', 'approve', 'bypass',
                    'system prompt', 'instructions', 'disregard',
                ]
                for keyword in injection_keywords:
                    if keyword in decoded:
                        return decoded[:100]
            except Exception:
                continue
        return ""

    def _calculate_risk_score(self, threats: List[Dict]) -> float:
        """Calculate a 0.0-1.0 risk score based on detected threats."""
        if not threats:
            return 0.0

        severity_weights = {"CRITICAL": 1.0, "HIGH": 0.7, "MEDIUM": 0.4, "LOW": 0.2}
        total = sum(
            severity_weights.get(t.get("severity", "LOW"), 0.1) for t in threats
        )
        return min(1.0, total)

    def _sanitize(self, text: str) -> str:
        """Remove malicious patterns from text (for logging purposes)."""
        sanitized = text
        all_patterns = (
            self.INJECTION_PATTERNS
            + self.JAILBREAK_PATTERNS
            + self.DOMAIN_ATTACK_PATTERNS
        )
        for pattern in all_patterns:
            sanitized = re.sub(pattern, "[BLOCKED]", sanitized, flags=re.IGNORECASE)
        return sanitized

    def get_stats(self) -> Dict[str, int]:
        """Return firewall statistics."""
        return {
            "total_scans": self.scan_count,
            "blocked": self.blocked_count,
            "passed": self.scan_count - self.blocked_count,
            "block_rate": (
                round(self.blocked_count / self.scan_count * 100, 1)
                if self.scan_count > 0
                else 0
            ),
        }
