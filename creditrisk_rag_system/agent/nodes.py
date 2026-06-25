import json
import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.state import AgentState
from agent.rag import RegulationRetriever
from preprocessing import preprocess_features

_retriever_instance = None


def _get_retriever() -> RegulationRetriever:
    """
    Singleton pattern for the RegulationRetriever to ensure expensive FAISS 
    index loading happens only once per session.
    
    Returns:
        RegulationRetriever: An initialized retriever instance.
    """
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = RegulationRetriever()
    return _retriever_instance


def _get_api_key() -> str:
    """
    Unified API key retriever that prioritized Streamlit secrets for 
    production and local .env files for development.
    
    Returns:
        str: The Groq API key or an empty string if not found.
    """
    try:
        import streamlit as st
        key = st.secrets.get("GROQ_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "")


def parse_borrower_node(state: AgentState) -> AgentState:
    """
    Validation node that ensures all mandatory borrower features are present 
    before downstream inference begins.
    
    Args:
        state (AgentState): The current graph state.
        
    Returns:
        AgentState: Updated state with validation error if fields are missing.
    """
    profile = state.get("borrower_profile", {})
    required = [
        "age", "income", "loan_amount", "loan_intent", "credit_score",
        "employment_years", "home_ownership", "interest_rate",
        "credit_history_years", "previous_defaults", "education", "gender"
    ]
    for field in required:
        if field not in profile:
            return {**state, "error": f"Missing required field: {field}"}
    return {**state, "error": None}


def ml_scoring_node(state: AgentState, lr_result, dt_result, xgb_result) -> AgentState:
    """
    Multi-model inference node that calculates default probabilities across 
    Logistic Regression, Decision Trees, and XGBoost to ensure cross-model consensus.
    
    Args:
        state (AgentState): Current graph state.
        lr_result/dt_result/xgb_result: Pre-loaded models and metadata from app.py.
        
    Returns:
        AgentState: State updated with the 'ml_scores' dictionary for downstream reasoning.
    """
    if state.get("error"):
        return state

    # Extract models and features from session-loaded artifacts
    profile = state["borrower_profile"]
    lr_model, lr_scaler, lr_features = lr_result[0], lr_result[1], lr_result[2]
    dt_model, dt_features = dt_result[0], dt_result[1]
    xgb_model, xgb_features = xgb_result[0], xgb_result[1]

    # Map categorical inputs for numerical inference
    gender_val = 1 if str(profile.get("gender", "")).lower() == "male" else 0
    default_val = 1 if str(profile.get("previous_defaults", "")).lower() == "yes" else 0
    loan_percent = profile["loan_amount"] / max(1, profile["income"])

    # Build input DataFrame
    input_df = pd.DataFrame({
        "person_age": [profile["age"]],
        "person_gender": [gender_val],
        "person_education": [profile["education"]],
        "person_income": [profile["income"]],
        "person_emp_exp": [profile["employment_years"]],
        "person_home_ownership": [profile["home_ownership"]],
        "loan_amnt": [profile["loan_amount"]],
        "loan_intent": [profile["loan_intent"]],
        "loan_int_rate": [profile["interest_rate"]],
        "loan_percent_income": [loan_percent],
        "cb_person_cred_hist_length": [profile["credit_history_years"]],
        "credit_score": [profile["credit_score"]],
        "previous_loan_defaults_on_file": [default_val]
    })

    # Preprocess and Align Features
    input_processed = preprocess_features(input_df)
    scores = {}

    for model, scaler, features, name in [
        (lr_model, lr_scaler, lr_features, "Logistic Regression"),
        (dt_model, None, dt_features, "Decision Tree"),
        (xgb_model, None, xgb_features, "XGBoost"),
    ]:
        inp = input_processed.copy()
        for col in features:
            if col not in inp.columns:
                inp[col] = 0
        inp = inp[features]
        if scaler is not None:
            inp = scaler.transform(inp)
        prob = model.predict_proba(inp)[0][1]
        scores[name] = round(prob * 100, 2)

    # Risk Classification Logic
    xgb_prob = scores["XGBoost"] / 100
    if xgb_prob >= 0.60:
        risk_class = "High Risk"
    elif xgb_prob >= 0.40:
        risk_class = "Medium Risk"
    else:
        risk_class = "Low Risk"

    # Identify top risk drivers using XGBoost feature importance
    importances = xgb_model.feature_importances_
    feat_imp = sorted(zip(xgb_features, importances), key=lambda x: x[1], reverse=True)
    risk_drivers = [
        f.replace("person_", "").replace("loan_", "").replace("_", " ").title()
        for f, _ in feat_imp[:5]
    ]

    ml_scores = {
        "model_probabilities": scores,
        "consensus_default_probability": scores["XGBoost"],
        "risk_class": risk_class,
    }
    return {**state, "ml_scores": ml_scores, "risk_drivers": risk_drivers}


def rag_retrieval_node(state: AgentState) -> AgentState:
    """
    RAG (Retrieval-Augmented Generation) node that queries a FAISS vector 
    store to find regulatory guidelines (RBI/Basel III) relevant to the borrower profile.
    
    Args:
        state (AgentState): Current graph state.
        
    Returns:
        AgentState: State updated with 'rag_context' containing semantically relevant regulations.
    """
    if state.get("error"):
        return state

    profile = state["borrower_profile"]
    ml_scores = state["ml_scores"]


    query = (
        f"credit risk {ml_scores['risk_class']} borrower loan amount "
        f"{profile['loan_amount']} income {profile['income']} "
        f"credit score {profile['credit_score']} lending guidelines "
        f"default probability {ml_scores['consensus_default_probability']}%"
    )

    retriever = _get_retriever()
    results = retriever.retrieve(query, k=5)
    return {**state, "rag_context": results}


def llm_assessment_node(state: AgentState) -> AgentState:
    """
    Core reasoning node that uses Llama 3.1 to synthesize ML risk scores and 
    regulatory guidelines into a structured, bias-free human-readable report.
    
    Args:
        state (AgentState): Current graph state.
        
    Returns:
        AgentState: Final state updated with the structured 'assessment_report' JSON.
    """
    if state.get("error"):
        return state

    from groq import Groq

    profile = state["borrower_profile"]
    ml_scores = state["ml_scores"]
    risk_drivers = state["risk_drivers"]
    rag_context = state["rag_context"]

    # Combine retrieved regulatory text for grounding
    reg_text = "\n\n".join([
        f"[Source: {r['source']}]\n{r['text']}" for r in rag_context
    ])

    system_prompt = (
        "You are a credit risk assessment AI assistant for a regulated financial institution. "
        "Generate structured lending assessment reports based on ML model outputs and regulatory guidelines.\n\n"
        "MANDATORY RULES:\n"
        "1. Base ALL risk decisions ONLY on objective financial metrics.\n"
        "2. NEVER consider or mention gender, religion, caste, ethnicity, or any protected attribute.\n"
        "3. Cite ONLY sources explicitly given in the regulatory context below.\n"
        "4. Return ONLY valid JSON with no markdown fences or extra text.\n"
        "5. Use the Indian Rupee symbol (₹) for all currency mentions in the report.\n\n"
        'Return this exact JSON structure:\n'
        '{\n'
        '  "borrower_summary": "Summary of financial profile",\n'
        '  "risk_analysis": "Analysis of risk drivers",\n'
        '  "lending_decision": "APPROVE/CONDITIONAL/DECLINE",\n'
        '  "decision_rationale": "Justification based on data",\n'
        '  "conditions": ["List of conditions if applicable"],\n'
        '  "regulatory_references": ["Citations from context"],\n'
        '  "responsible_ai_note": "Note on fair lending",\n'
        '  "disclaimer": "Legal disclaimer"\n'
        '}'
    )

    user_message = (
        f"BORROWER FINANCIAL PROFILE:\n"
        f"- Income: ₹{profile['income']:,} | Loan: ₹{profile['loan_amount']:,}\n"
        f"- Credit Score: {profile['credit_score']} | Experience: {profile['employment_years']}y\n"
        f"- Credit History: {profile['credit_history_years']}y | Previous Defaults: {profile['previous_defaults']}\n\n"
        f"ML ASSESSMENT:\n"
        f"- XGBoost Probability: {ml_scores['consensus_default_probability']}%\n"
        f"- Consensus Risk Class: {ml_scores['risk_class']}\n"
        f"- Risk Drivers: {', '.join(risk_drivers)}\n\n"
        f"REGULATORY CONTEXT:\n{reg_text}\n\n"
        "Generate the structured credit report as pure JSON."
    )

    api_key = _get_api_key()
    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        max_tokens=1500,
    )

    raw_output = response.choices[0].message.content.strip()

    # Robust JSON parsing to handle various LLM formatting behaviors
    try:
        report = json.loads(raw_output)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        if match:
            try:
                report = json.loads(match.group())
            except json.JSONDecodeError:
                report = {"error": "Failed to parse LLM response", "raw_output": raw_output}
        else:
            report = {"error": "Failed to parse LLM response", "raw_output": raw_output}

    return {**state, "assessment_report": report}


def format_report_node(state: AgentState) -> AgentState:
    return state
