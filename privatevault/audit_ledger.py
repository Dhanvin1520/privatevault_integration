"""
Audit Ledger — Merkle-Chained Immutable Audit Trail
Adapted from PrivateVault.ai's decision_ledger.py

Creates a tamper-evident, append-only log of all governance decisions
with SHA-256 hash chaining for integrity verification.
"""

import json
import hashlib
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger("privatevault.audit_ledger")

GENESIS_HASH = "0" * 64


class AuditLedger:
    """
    Merkle-chained append-only audit trail for AI governance decisions.

    Every entry is hash-chained to its predecessor, creating a tamper-evident
    log that can be independently verified. Adapted from PrivateVault's
    DecisionLedger: https://github.com/LOLA0786/PrivateVault.ai/blob/main/decision_ledger.py

    Event types:
        PROMPT_SCAN, PII_DETECTED, PII_REDACTED, POLICY_CHECK,
        POLICY_VIOLATION, CONTEXT_VALIDATION, CONTEXT_POISONING_DETECTED,
        HALLUCINATION_CHECK, DECISION_RENDERED, DECISION_BLOCKED
    """

    def __init__(self, log_file: str = "audit_ledger.jsonl"):
        self.log_file = log_file
        self.chain: List[Dict[str, Any]] = []
        self.previous_hash: str = GENESIS_HASH

        if not os.path.exists(self.log_file):
            os.makedirs(os.path.dirname(self.log_file) or ".", exist_ok=True)
            open(self.log_file, "a").close()
        else:
            self._load_from_file()

    def log_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        outcome: str = "RECORDED",
    ) -> Dict[str, Any]:
        """
        Append a new event to the audit ledger.

        Args:
            event_type: Category of the event (e.g., PROMPT_SCAN)
            data: Event-specific data payload
            outcome: Result of the governance action

        Returns:
            The complete ledger entry with hash
        """
        entry = {
            "index": len(self.chain),
            "timestamp": self._utc_now_iso(),
            "event_type": event_type,
            "outcome": outcome,
            "data": data,
            "previous_hash": self.previous_hash,
        }

        entry["hash"] = self._calculate_hash(entry)

        self.chain.append(entry)
        self.previous_hash = entry["hash"]
        self._append_to_file(entry)

        return entry

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify the entire audit chain for tampering.

        Returns:
            Dict with: is_valid, total_entries, errors[]
        """
        if not self.chain:
            return {"is_valid": True, "total_entries": 0, "errors": []}

        errors = []
        expected_prev_hash = GENESIS_HASH

        for i, entry in enumerate(self.chain):
            if entry.get("index") != i:
                errors.append(f"Entry {i}: Invalid index (got {entry.get('index')})")

            if entry.get("previous_hash") != expected_prev_hash:
                errors.append(
                    f"Entry {i}: Broken hash chain "
                    f"(expected {expected_prev_hash[:16]}..., "
                    f"got {entry.get('previous_hash', '')[:16]}...)"
                )

            entry_copy = {k: v for k, v in entry.items() if k != "hash"}
            recalculated = self._calculate_hash(entry_copy)
            if recalculated != entry.get("hash"):
                errors.append(
                    f"Entry {i}: Hash mismatch (tampered?)"
                )

            expected_prev_hash = entry.get("hash", "")

        return {
            "is_valid": len(errors) == 0,
            "total_entries": len(self.chain),
            "errors": errors,
        }

    def get_entries_by_type(self, event_type: str) -> List[Dict]:
        """Filter ledger entries by event type."""
        return [e for e in self.chain if e.get("event_type") == event_type]

    def get_summary(self) -> Dict[str, Any]:
        """Generate a compliance-friendly summary of the audit trail."""
        type_counts = {}
        outcome_counts = {}

        for entry in self.chain:
            et = entry.get("event_type", "UNKNOWN")
            type_counts[et] = type_counts.get(et, 0) + 1

            oc = entry.get("outcome", "UNKNOWN")
            outcome_counts[oc] = outcome_counts.get(oc, 0) + 1

        integrity = self.verify_integrity()

        return {
            "total_entries": len(self.chain),
            "event_types": type_counts,
            "outcomes": outcome_counts,
            "chain_integrity": integrity["is_valid"],
            "integrity_errors": len(integrity["errors"]),
            "first_entry": (
                self.chain[0]["timestamp"] if self.chain else None
            ),
            "last_entry": (
                self.chain[-1]["timestamp"] if self.chain else None
            ),
        }

    def export_human_readable(self) -> str:
        """Export the ledger as a human-readable text report."""
        lines = [
            "=" * 60,
            "PRIVATEVAULT AUDIT LEDGER — COMPLIANCE REPORT",
            "=" * 60,
            "",
        ]

        for entry in self.chain:
            lines.append(
                f"[{entry['index']:04d}] {entry['timestamp']} | "
                f"{entry['event_type']} | {entry['outcome']}"
            )
            if entry.get("data"):
                data_str = json.dumps(entry["data"], indent=None)
                if len(data_str) > 200:
                    data_str = data_str[:200] + "..."
                lines.append(f"       Data: {data_str}")
            lines.append(f"       Hash: {entry['hash'][:32]}...")
            lines.append("")

        integrity = self.verify_integrity()
        lines.append("=" * 60)
        lines.append(
            f"CHAIN INTEGRITY: {'✓ VALID' if integrity['is_valid'] else '✗ TAMPERED'}"
        )
        lines.append(f"TOTAL ENTRIES: {len(self.chain)}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _calculate_hash(self, entry: Dict[str, Any]) -> str:
        """Calculate SHA-256 hash of entry (excluding 'hash' field)."""
        canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _append_to_file(self, entry: Dict[str, Any]):
        """Append entry to JSONL file."""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
            f.flush()

    def _load_from_file(self):
        """Load existing entries from file and rebuild chain state."""
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        self.chain.append(entry)
                        self.previous_hash = entry.get("hash", GENESIS_HASH)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("Could not load existing audit ledger, starting fresh")
            self.chain = []
            self.previous_hash = GENESIS_HASH

    def _utc_now_iso(self) -> str:
        return (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            + "Z"
        )

    def clear(self):
        """Clear the ledger (for testing only)."""
        self.chain = []
        self.previous_hash = GENESIS_HASH
        open(self.log_file, "w").close()
