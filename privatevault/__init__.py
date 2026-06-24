"""
PrivateVault Coordination Layer
Runtime governance infrastructure for AI systems.

Adapted from: https://github.com/LOLA0786/PrivateVault.ai
Integrated into: Credit Risk RAG System
"""

from .firewall import AIFirewall
from .pii_shield import PIIShield
from .policy_engine import LendingPolicyEngine
from .context_validator import ContextValidator
from .hallucination_guard import HallucinationGuard
from .audit_ledger import AuditLedger

__version__ = "1.0.0"

__all__ = [
    "AIFirewall",
    "PIIShield",
    "LendingPolicyEngine",
    "ContextValidator",
    "HallucinationGuard",
    "AuditLedger",
]
