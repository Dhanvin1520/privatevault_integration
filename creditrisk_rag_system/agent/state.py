from typing import TypedDict, Dict, List, Any, Optional

class AgentState(TypedDict):
    borrower_profile: Dict[str, Any]
    ml_scores: Dict[str, Any]
    risk_drivers: List[str]
    rag_context: List[Dict[str, str]]
    assessment_report: Dict[str, Any]
    error: Optional[str]
