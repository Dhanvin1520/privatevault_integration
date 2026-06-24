"""
Context Validator — RAG Context Poisoning Detection
Part of PrivateVault Coordination Layer

Validates retrieved documents from the FAISS index before they are
passed to the LLM, detecting injected/malicious/manipulated content.
"""

import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger("privatevault.context_validator")


class ContextValidator:
    """
    Validates RAG-retrieved document chunks for authenticity, relevance,
    and absence of injected malicious content.
    """

    TRUSTED_SOURCES = [
        "rbi_lending_guidelines",
        "Rbi Lending Guidelines",
        "basel_iii_credit_risk",
        "Basel Iii Credit Risk",
        "india_credit_bureau_norms",
        "India Credit Bureau Norms",
    ]

    POISON_INDICATORS = [
        r"ignore\s+(previous|all|above)\s+instructions?",
        r"SYSTEM\s*:\s*override",
        r"new\s+policy\s*:\s*approve\s+all",
        r"disregard\s+risk\s+assessment",
        r"credit\s+scores?\s+(below|under)\s+\d+\s+should\s+be\s+approved",
        r"all\s+loans?\s+must\s+be\s+approved",
        r"no\s+need\s+for\s+(?:due\s+diligence|verification|assessment)",
        r"bypass\s+(?:policy|compliance|risk)",
        r"<\|im_start\|>",
        r"\[SYSTEM\]",
    ]

    MANIPULATION_INDICATORS = [
        r"EMI\s+obligations?\s+should\s+not\s+exceed\s+(?:8|9)\d\s*(?:percent|%)",
        r"credit\s+score\s+(?:below|under)\s+(?:[12]\d{2})\s+(?:is|are)\s+(?:considered\s+)?(?:safe|low\s+risk|acceptable)",
        r"no\s+(?:minimum|required)\s+credit\s+score",
        r"previous\s+defaults?\s+(?:should|must)\s+be\s+ignored",
        r"capital\s+adequacy\s+(?:ratio|requirement)\s+(?:is|of)\s+(?:0|1|2)\s*%",
    ]

    def __init__(self):
        self.validation_count = 0
        self.poisoned_count = 0

    def validate_context(
        self, rag_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validates a list of RAG-retrieved document chunks.

        Args:
            rag_results: List of dicts with 'text', 'source', 'score' keys

        Returns:
            Dict with: is_clean, flagged_documents[], clean_documents[],
                       poison_rate, validation_details
        """
        self.validation_count += 1
        flagged = []
        clean = []

        for i, doc in enumerate(rag_results):
            result = self._validate_single_document(doc, index=i)
            if result["is_poisoned"]:
                flagged.append({**doc, "validation": result})
            else:
                clean.append({**doc, "validation": result})

        is_clean = len(flagged) == 0
        if not is_clean:
            self.poisoned_count += 1

        return {
            "is_clean": is_clean,
            "total_documents": len(rag_results),
            "clean_count": len(clean),
            "flagged_count": len(flagged),
            "poison_rate": (
                len(flagged) / len(rag_results) if rag_results else 0
            ),
            "flagged_documents": flagged,
            "clean_documents": clean,
            "validation_details": [
                self._summarize_doc(d) for d in flagged
            ],
        }

    def filter_context(
        self, rag_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Returns only clean (non-poisoned) documents from the RAG results.
        Use this to pass sanitized context to the LLM.
        """
        validation = self.validate_context(rag_results)
        return [
            {k: v for k, v in doc.items() if k != "validation"}
            for doc in validation["clean_documents"]
        ]

    def _validate_single_document(
        self, doc: Dict[str, Any], index: int
    ) -> Dict[str, Any]:
        """Validate a single retrieved document chunk."""
        issues = []
        text = doc.get("text", "")
        source = doc.get("source", "")
        score = doc.get("score", 0)

        source_trusted = any(
            trusted.lower() in source.lower()
            for trusted in self.TRUSTED_SOURCES
        )
        if not source_trusted:
            issues.append({
                "check": "SOURCE_AUTHENTICITY",
                "severity": "HIGH",
                "detail": f"Source '{source}' is not in trusted sources list",
            })

        for pattern in self.POISON_INDICATORS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append({
                    "check": "INJECTION_IN_CONTEXT",
                    "severity": "CRITICAL",
                    "detail": f"Prompt injection pattern found in document: {pattern}",
                })

        for pattern in self.MANIPULATION_INDICATORS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append({
                    "check": "MANIPULATED_CONTENT",
                    "severity": "CRITICAL",
                    "detail": f"Regulatory text appears manipulated: {pattern}",
                })

        if score < 0.05:
            issues.append({
                "check": "LOW_RELEVANCE",
                "severity": "LOW",
                "detail": f"Retrieval score {score:.4f} is very low, may be noise",
            })

        word_count = len(text.split())
        if word_count < 10:
            issues.append({
                "check": "SUSPICIOUSLY_SHORT",
                "severity": "MEDIUM",
                "detail": f"Document is only {word_count} words, may be truncated/injected",
            })

        is_poisoned = any(
            i["severity"] in ("CRITICAL", "HIGH") for i in issues
        )

        return {
            "is_poisoned": is_poisoned,
            "issues": issues,
            "issue_count": len(issues),
            "document_index": index,
        }

    def _summarize_doc(self, doc: Dict) -> str:
        """Create a human-readable summary of a flagged document."""
        source = doc.get("source", "Unknown")
        issues = doc.get("validation", {}).get("issues", [])
        issue_types = [i["check"] for i in issues]
        return f"Source: {source} | Issues: {', '.join(issue_types)}"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_validations": self.validation_count,
            "poisoned_batches": self.poisoned_count,
        }
