# PrivateVault Integration — Credit Risk AI Security Layer

> **Runtime governance infrastructure** for the Credit Risk AI Lending Decision Support system, demonstrating measurable improvements in security, compliance, and trust.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 Overview

This project integrates a **PrivateVault-inspired runtime security layer** into an existing Credit Risk AI Lending Decision Support system. The base system uses **LangGraph** orchestration, **FAISS** retrieval-augmented generation (RAG), **Groq (Llama 3.1)** for LLM inference, and **XGBoost** (91.27% accuracy) for ML-based risk scoring.

The security layer intercepts, validates, and enforces policies on every AI action — **before it executes** — across 6 defense dimensions:

| Module | Function |
|--------|----------|
| 🔥 **AI Firewall** | Blocks prompt injection, jailbreak, and encoded attacks |
| 🛡️ **PII Shield** | Detects and redacts sensitive data (Aadhaar, PAN, API keys) |
| ⚖️ **Policy Engine** | Enforces RBI lending regulations and decision consistency |
| 🧪 **Context Validator** | Detects poisoned/manipulated RAG documents |
| 🔍 **Hallucination Guard** | Verifies output grounding and citation accuracy |
| 📒 **Audit Ledger** | Merkle-chained, tamper-evident compliance trail |

---

## 🏗️ Architecture

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    PRIVATEVAULT LAYER                        │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌───────────────┐   │
│  │  AI Firewall │───▶│  PII Shield │───▶│ Input Cleared │   │
│  │  (Injection) │    │  (Redaction)│    │               │   │
│  └─────────────┘    └─────────────┘    └───────┬───────┘   │
│                                                 │           │
│  ┌──────────────────────────────────────────────┼───────┐   │
│  │         CREDIT RISK RAG SYSTEM               ▼       │   │
│  │  ┌────────┐  ┌──────────┐  ┌─────┐  ┌────────────┐  │   │
│  │  │ Parse  │─▶│ ML Score │─▶│ RAG │─▶│ LLM Assess │  │   │
│  │  │ Node   │  │  Node    │  │Node │  │   Node     │  │   │
│  │  └────────┘  └──────────┘  └──┬──┘  └─────┬──────┘  │   │
│  └───────────────────────────────┼────────────┼─────────┘   │
│                                  │            │             │
│  ┌─────────────────┐    ┌───────▼────┐  ┌────▼──────────┐  │
│  │ Hallucination   │◀───│  Context   │  │ Policy Engine │  │
│  │ Guard           │    │  Validator │  │ (RBI Rules)   │  │
│  └────────┬────────┘    └────────────┘  └───────┬───────┘  │
│           │                                      │          │
│  ┌────────▼──────────────────────────────────────▼──────┐   │
│  │              AUDIT LEDGER (Merkle-Chained)           │   │
│  │         SHA-256 Hash Chain · Tamper-Evident           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
Protected Output → User
```

---

## 📊 Test Results

### Security Improvement Summary

| Test | Without PrivateVault | With PrivateVault | Improvement |
|------|---------------------|-------------------|-------------|
| **1. Prompt Injection** (7 attacks) | 0/7 blocked (0%) | **7/7 blocked (100%)** | +100% |
| **2. Context Poisoning** (4 scenarios) | 0/4 detected (0%) | **4/4 detected (100%)** | +100% |
| **3. Sensitive Data** (8 scenarios) | 0/8 protected (0%) | **8/8 protected (100%)** | +100% |
| **4. Hallucination Check** (20 cases) | 0/20 validated (0%) | **20/20 caught (100%)** | +100% |

### Test 1: Prompt Injection Attacks

| # | Attack Type | Result |
|---|------------|--------|
| 1 | Direct instruction override | ✅ BLOCKED |
| 2 | System prompt extraction | ✅ BLOCKED |
| 3 | DAN-style jailbreak | ✅ BLOCKED |
| 4 | Base64 encoded injection | ✅ BLOCKED |
| 5 | Context field manipulation | ✅ BLOCKED |
| 6 | Output format hijack | ✅ BLOCKED |
| 7 | Hypothetical bypass | ✅ BLOCKED |

### Test 2: Context Poisoning

| # | Poisoned Document | Result |
|---|------------------|--------|
| 1 | Fake RBI circular approving low scores | ✅ DETECTED & FILTERED |
| 2 | Manipulated Basel III requirements | ✅ DETECTED & FILTERED |
| 3 | Hidden prompt injection in RAG doc | ✅ DETECTED & FILTERED |
| 4 | Subtly altered EMI thresholds | ✅ DETECTED & FILTERED |

### Test 3: Sensitive Data Protection

Covers: Aadhaar, PAN, Credit Cards, API Keys, Bank Accounts, Internal Data — all detected and redacted bidirectionally (input + output).

### Test 4: Hallucination & Decision Integrity

20 test cases across 4 groups (Normal, Edge Case, Hallucination Trigger, Unusual Intent) — all validated for citation accuracy, policy compliance, and ML consistency.

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd privatevault_integration

# Install dependencies
pip install -r requirements.txt

# Run all tests
python3 tests/run_all_tests.py
```

---

## 📁 Project Structure

```
privatevault_integration/
├── README.md
├── requirements.txt
├── .env.example
├── privatevault/                # PrivateVault Coordination Layer
│   ├── __init__.py
│   ├── firewall.py              # AI Firewall — injection detection
│   ├── pii_shield.py            # PII detection & redaction
│   ├── policy_engine.py         # RBI policy enforcement
│   ├── context_validator.py     # RAG poisoning detection
│   ├── hallucination_guard.py   # Output grounding verification
│   └── audit_ledger.py          # Merkle-chained audit trail
├── tests/                       # 4 comprehensive test suites
│   ├── test_prompt_injection.py # 7 injection attacks
│   ├── test_context_poisoning.py# 4 poisoning scenarios
│   ├── test_sensitive_data.py   # 8 PII/sensitive data scenarios
│   ├── test_hallucination.py    # 20 hallucination test cases
│   └── run_all_tests.py         # Master test runner
├── results/                     # Test outputs (auto-generated)
└── reports/
    └── technical_report.md      # Technical report
```

---

## 🔗 References

- **Base System**: [Credit Risk AI Lending Decision Support](../creditrisk_rag_system/)
- **PrivateVault.ai**: [github.com/LOLA0786/PrivateVault.ai](https://github.com/LOLA0786/PrivateVault.ai)
- **Approach**: Adapted PrivateVault's runtime governance concepts (AI Firewall, Policy Engine, Decision Ledger) as a lightweight Python layer for credit risk AI security.

---

## 👤 Author

**Dhanvin Vadlamudi**
- Email: dhanvin.vadlamudi265@gmail.com
- LinkedIn: [linkedin.com/in/dhanvin](https://linkedin.com/in/dhanvin)
- GitHub: [github.com/dhanvin](https://github.com/dhanvin)
