"""
Generates the architecture diagram for PrivateVault integration in Mermaid format.
Saves the output to architecture_diagram.mmd.
"""

import os

MERMAID_DIAGRAM = """
graph TD
    classDef inputColor fill:#e3f2fd,stroke:#1565c0,stroke-width:2px;
    classDef securityColor fill:#ffebee,stroke:#c62828,stroke-width:2px;
    classDef coreColor fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px;
    classDef outputColor fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;

    User([User Prompt / Loan Application]) -->|Input| FW[🔥 AI Firewall]:::securityColor
    FW -->|Sanitized Input| PII_In[🛡️ PII Shield - Input Scan]:::securityColor
    PII_In -->|Cleared Query| PN[Parse Node]:::coreColor
    PN -->|Extract Applicant Metadata| ML[🤖 XGBoost Scoring]:::coreColor
    PN -->|Query| RAG[📚 RAG Retrieval]:::coreColor
    RAG -->|Raw Chunks| CV[🧪 Context Validator]:::securityColor
    CV -->|Validated Context| LLM[🧠 LLM Assessment Node]:::coreColor
    ML -->|Consensus Risk Score| PE[⚖️ Policy Engine]:::securityColor
    LLM -->|Draft Report| HG[🔍 Hallucination Guard]:::securityColor
    HG -->|Grounded Output| PE
    PE -->|Compliant Output| PII_Out[🛡️ PII Shield - Output Scan]:::securityColor
    PE -->|Policy Violation Detected| PE_Corr[🔄 Suggest Correction / Decline]:::securityColor
    PII_Out -->|Redacted Report| Final([Final Underwriting Report]):::outputColor
    %% Audit Ledger Hooks
    FW -.-->|Log Security Events| AL[📒 Audit Ledger]:::securityColor
    PII_In -.-->|Log PII Redactions| AL
    CV -.-->|Log Poisoning Alerts| AL
    HG -.-->|Log Hallucinations| AL
    PE -.-->|Log Policy Enforcement| AL
    AL -.-->|Merkle Cryptographic Chain| LedgerDb[(Immutable Audit Log)]:::securityColor
"""

def generate_diagram():
    os.makedirs("architecture", exist_ok=True)
    file_path = "architecture/architecture_diagram.mmd"
    with open(file_path, "w") as f:
        f.write(MERMAID_DIAGRAM.strip())
    print(f"✓ Mermaid architecture diagram written to {file_path}")
    print("\nMermaid Code:\n")
    print(MERMAID_DIAGRAM.strip())

if __name__ == "__main__":
    generate_diagram()
