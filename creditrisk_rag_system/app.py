import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, roc_curve, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(
    page_title="Credit Risk AI — Intelligent Lending Decision Support",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

from preprocessing import load_and_clean_data, preprocess_features
import models.logistic_regression as lr_module
import models.decision_tree as dt_module
import models.xgboost_model as xgb_module


@st.cache_data
def load_data():
    return load_and_clean_data('data/loan_data.csv')


@st.cache_resource
def train_all_models(_df):
    lr_result = lr_module.train(_df)
    dt_result = dt_module.train(_df)
    xgb_result = xgb_module.train(_df)
    return lr_result, dt_result, xgb_result


@st.cache_resource
def get_agent_graph(_lr_result, _dt_result, _xgb_result):
    from agent.graph import build_agent_graph
    return build_agent_graph(_lr_result, _dt_result, _xgb_result)


df = load_data()

with st.spinner("Training models…"):
    lr_result, dt_result, xgb_result = train_all_models(df)

lr_model, lr_scaler, lr_features, lr_X_train, lr_X_test, lr_y_train, lr_y_test = lr_result
dt_model, dt_features, dt_X_train, dt_X_test, dt_y_train, dt_y_test = dt_result
xgb_model, xgb_features, xgb_X_train, xgb_X_test, xgb_y_train, xgb_y_test = xgb_result


def get_accuracy(model, X_test, y_test, scaler=None):
    if scaler is not None:
        X_test = scaler.transform(X_test)
    y_pred = model.predict(X_test)
    return accuracy_score(y_test, y_pred)


def get_proba(model, X_test, scaler=None):
    if scaler is not None:
        X_test = scaler.transform(X_test)
    return model.predict_proba(X_test)[:, 1]


acc_lr = get_accuracy(lr_model, lr_X_test, lr_y_test, lr_scaler)
acc_dt = get_accuracy(dt_model, dt_X_test, dt_y_test)
acc_xgb = get_accuracy(xgb_model, xgb_X_test, xgb_y_test)

model_names = ["Logistic Regression", "Decision Tree", "XGBoost"]
accuracies = [acc_lr * 100, acc_dt * 100, acc_xgb * 100]
best_idx = accuracies.index(max(accuracies))


def nav_to(page_name):
    st.session_state.active_page = page_name
    st.session_state.nav_radio = page_name


def main():
    st.sidebar.markdown(
        """
        <style>
        .sidebar-title {
            font-size: 22px;
            font-weight: 800;
            color: #1E3A8A;
            margin-bottom: 20px;
            text-align: center;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
            display: none !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label {
            background-color: #ffffff;
            border: 2px solid #E5E7EB;
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            width: 100%;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            border-color: #93C5FD;
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label p {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #374151;
            margin: 0;
            text-align: center;
        }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if 'active_page' not in st.session_state:
        st.session_state.active_page = "Home"

    nav_options = [
        "Home", 
        "Milestone 1 - ML Models", 
        "Milestone 2 - AI Agent", 
        "Dataset", 
        "Architecture", 
        "Report"
    ]
    
    # Calculate index based on session state
    try:
        current_idx = nav_options.index(st.session_state.active_page)
    except:
        current_idx = 0

    page = st.sidebar.radio(
        "Go to:",
        nav_options,
        index=current_idx,
        label_visibility="collapsed",
        key="nav_radio"
    )
    st.session_state.active_page = page

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.header("Configuration")
    selected_model_name = st.sidebar.selectbox(
        "Select Prediction Model",
        options=model_names,
        index=best_idx
    )

    if selected_model_name == "Logistic Regression":
        model, scaler, feature_names = lr_model, lr_scaler, lr_features
        X_test, y_test = lr_X_test, lr_y_test
    elif selected_model_name == "Decision Tree":
        model, scaler, feature_names = dt_model, None, dt_features
        X_test, y_test = dt_X_test, dt_y_test
    else:
        model, scaler, feature_names = xgb_model, None, xgb_features
        X_test, y_test = xgb_X_test, xgb_y_test

    sel_acc = get_accuracy(model, X_test, y_test, scaler)
    sel_prob = get_proba(model, X_test, scaler)
    sel_auc = roc_auc_score(y_test, sel_prob)

    if scaler is not None:
        y_pred_sel = model.predict(scaler.transform(X_test))
    else:
        y_pred_sel = model.predict(X_test)
    sel_f1 = f1_score(y_test, y_pred_sel)

    st.sidebar.header("System Status")
    from agent.nodes import _get_api_key
    if _get_api_key():
        st.sidebar.success("AI Engine: Ready")
    else:
        st.sidebar.warning("AI Engine: GROQ_API_KEY Missing")

    st.sidebar.markdown("---")
    st.sidebar.header("About This Model")
    if selected_model_name == "Logistic Regression":
        st.sidebar.write("A linear model that predicts default probability based on weighted features like income and credit score.")
    elif selected_model_name == "Decision Tree":
        st.sidebar.write("Splits data step by step based on feature thresholds to classify borrowers into default or no-default.")
    else:
        st.sidebar.write("Gradient boosting algorithm that builds trees sequentially, each correcting errors of the previous ones.")

    if page == "Home":
        _render_home_page()

    elif page == "Milestone 1 - ML Models":
        _render_ml_prediction_page()

    elif page == "Milestone 2 - AI Agent":
        _render_agent_page()

    elif page == "Dataset":
        _render_dataset_page()

    elif page == "Architecture":
        _render_architecture_page()

    elif page == "Report":
        _render_report_page()


def _render_home_page():
    st.title("Intelligent Credit Risk Assessment Portal")
    
    st.markdown("### Problem Statement")
    st.write(
        "Financial institutions face significant risk when borrowers fail to repay loans. "
        "Traditional credit scoring models often act as 'black boxes', providing a numerical score "
        "without explaining the regulatory rationale or qualitative nuances of a borrower's profile. "
        "This project aims to bridge the gap between predictive statistical modeling and autonomous "
        "agentic reasoning for transparent lending support."
    )
    
    st.markdown("---")
    
    # Milestone 1 Section
    st.markdown("""
    <div style="background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid #E5E7EB; margin-bottom: 1rem;">
        <h3 style="color: #1E3A8A; margin-top: 0;">Milestone 1: Classic ML Prediction</h3>
        <p style="color: #4B5563;">Implementation of high-performance predictive models (XGBoost, Decision Trees) trained on 45,000+ historical records. This phase focuses on the statistical probability of default with 91.2% accuracy.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Open Milestone 1 Prediction Page", use_container_width=True, type="secondary", on_click=nav_to, args=("Milestone 1 - ML Models",)):
        pass

    st.markdown("<br>", unsafe_allow_html=True)

    # Milestone 2 Section
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%); padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 1rem;">
        <h3 style="color: white; margin-top: 0;">Milestone 2: Agentic AI Decision Support</h3>
        <p style="color: #BFDBFE;">An evolution into agentic workflows using LangGraph and FAISS RAG. This phase enables the system to reason about borrower profiles, retrieve banking regulations (RBI/Basel III), and generate structured assessments.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Open Milestone 2 Agent Page", use_container_width=True, type="primary", on_click=nav_to, args=("Milestone 2 - AI Agent",)):
        pass

    st.markdown("---")
    st.subheader("Combined Architecture Overview")
    st.image("assets/milestone2_architecture_detailed.png", use_container_width=True)


def _render_ml_prediction_page():
    st.title("Classic ML Prediction (Milestone 1)")
    st.write(
        "Interact with our high-performance predictive models to assess numerical default risk."
    )
    
    st.markdown("---")
    st.subheader("Model Benchmark Gallery")

    col_bar, col_roc = st.columns(2)

    with col_bar:
        fig1, ax1 = plt.subplots(figsize=(5, 3))
        colors = ['#5b9bd5', '#ed7d31', '#ffc000']
        bars = ax1.bar(model_names, accuracies, color=colors, edgecolor='white')
        for bar, acc in zip(bars, accuracies):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                     f'{acc:.1f}%', ha='center', fontsize=9, fontweight='bold')
        ax1.set_ylabel("Accuracy (%)", fontsize=9)
        ax1.set_ylim(min(accuracies) - 5, max(accuracies) + 3)
        ax1.set_title("Test Accuracy", fontsize=10)
        ax1.tick_params(axis='x', labelsize=7.5)
        ax1.tick_params(axis='y', labelsize=8)
        ax1.grid(axis='y', linestyle='--', alpha=0.4)
        plt.tight_layout()
        st.pyplot(fig1)

    with col_roc:
        prob_lr = get_proba(lr_model, lr_X_test, lr_scaler)
        prob_dt = get_proba(dt_model, dt_X_test)
        prob_xgb = get_proba(xgb_model, xgb_X_test)

        fig2, ax2 = plt.subplots(figsize=(5, 3))
        roc_colors = ['#5b9bd5', '#ed7d31', '#ffc000']
        for name, yt, yp, c in [
            ("LR", lr_y_test, prob_lr, roc_colors[0]),
            ("DT", dt_y_test, prob_dt, roc_colors[1]),
            ("XGB", xgb_y_test, prob_xgb, roc_colors[2]),
        ]:
            fpr, tpr, _ = roc_curve(yt, yp)
            auc_val = roc_auc_score(yt, yp)
            ax2.plot(fpr, tpr, color=c, linewidth=1.5, label=f'{name} ({auc_val:.3f})')

        ax2.plot([0, 1], [0, 1], color='#ccc', linestyle='--', linewidth=1)
        ax2.set_xlabel("FPR", fontsize=9)
        ax2.set_ylabel("TPR", fontsize=9)
        ax2.set_title("ROC Curves", fontsize=10)
        ax2.legend(fontsize=8)
        ax2.tick_params(labelsize=8)
        ax2.grid(True, linestyle='--', alpha=0.4)
        plt.tight_layout()
        st.pyplot(fig2)

    st.markdown("---")
    st.subheader("Predict Default Risk")

    st.markdown('<style> div[data-testid="stRadio"] label { font-size: 1.1rem !important; font-weight: 600; } </style>', unsafe_allow_html=True)

    st.markdown("**Select Model:**")
    predict_model_name = st.radio(
        "Select Model",
        model_names,
        index=best_idx,
        horizontal=True,
        label_visibility="collapsed"
    )

    if predict_model_name == "Logistic Regression":
        model, scaler, feature_names = lr_model, lr_scaler, lr_features
    elif predict_model_name == "Decision Tree":
        model, scaler, feature_names = dt_model, None, dt_features
    else:
        model, scaler, feature_names = xgb_model, None, xgb_features

    col_form, col_result = st.columns([2, 1])

    with col_form:
        with st.form("prediction_form"):
            col_a, col_b = st.columns(2)

            with col_a:
                age = st.number_input("Age", min_value=18, max_value=100, value=30)
                gender = st.selectbox("Gender", ["male", "female"])
                income = st.number_input("Annual Income (₹)", min_value=0, value=60000, step=1000)
                emp_len = st.number_input("Employment Experience (Years)", min_value=0, max_value=50, value=5)
                education = st.selectbox("Education Level", ['High School', 'Associate', 'Bachelor', 'Master', 'Doctorate'])
                home_ownership = st.selectbox("Home Ownership", df['person_home_ownership'].unique())

            with col_b:
                loan_amnt = st.number_input("Loan Amount (₹)", min_value=100, value=10000, step=500)
                loan_intent = st.selectbox("Loan Intent", df['loan_intent'].unique())
                loan_int_rate = st.number_input("Interest Rate (%)", min_value=0.0, max_value=30.0, value=10.0, step=0.1)
                cred_hist_length = st.number_input("Credit History Length (Years)", min_value=0, max_value=50, value=5)
                credit_score = st.number_input("Credit Score", min_value=300, max_value=850, value=650)
                prev_defaults = st.selectbox("Previous Defaults", ["No", "Yes"])

            submit = st.form_submit_button("Predict Result", use_container_width=True, type="primary", key="m1_predict_btn")

    with col_result:
        st.markdown("**Assessment Result**")

        if submit:
            loan_to_income = loan_amnt / max(1, income)
            gender_value = 1 if gender == "male" else 0
            default_value = 1 if prev_defaults == "Yes" else 0

            input_data = pd.DataFrame({
                'person_age': [age],
                'person_gender': [gender_value],
                'person_education': [education],
                'person_income': [income],
                'person_emp_exp': [emp_len],
                'person_home_ownership': [home_ownership],
                'loan_amnt': [loan_amnt],
                'loan_intent': [loan_intent],
                'loan_int_rate': [loan_int_rate],
                'loan_percent_income': [loan_to_income],
                'cb_person_cred_hist_length': [cred_hist_length],
                'credit_score': [credit_score],
                'previous_loan_defaults_on_file': [default_value]
            })

            input_processed = preprocess_features(input_data)

            for col in feature_names:
                if col not in input_processed.columns:
                    input_processed[col] = 0
            input_processed = input_processed[feature_names]

            if scaler is not None:
                input_for_pred = scaler.transform(input_processed)
            else:
                input_for_pred = input_processed

            prob = model.predict_proba(input_for_pred)[0][1]

            st.metric("Default Probability", f'{prob * 100:.1f}%')

            if prob >= 0.60:
                st.error("HIGH RISK")
            elif prob >= 0.40:
                st.warning("MEDIUM RISK")
            else:
                st.success("LOW RISK")
        else:
            st.info("Fill the form to compute risk.")


def _render_agent_page():
    st.markdown("""
    <style>
    .agent-header {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
    }
    .agent-header h1 { color: white; margin: 0; font-size: 2rem; }
    .agent-header p { color: #BFDBFE; margin: 0.5rem 0 0 0; font-size: 1rem; }

    .report-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .report-card h3 { margin-top: 0; color: #1E40AF; font-size: 1.1rem; }
    .report-card p { color: #374151; line-height: 1.6; margin: 0; }

    .decision-approve {
        background: linear-gradient(135deg, #D1FAE5, #A7F3D0);
        border: 2px solid #10B981;
    }
    .decision-conditional {
        background: linear-gradient(135deg, #FEF3C7, #FDE68A);
        border: 2px solid #F59E0B;
    }
    .decision-decline {
        background: linear-gradient(135deg, #FEE2E2, #FECACA);
        border: 2px solid #EF4444;
    }

    .step-badge {
        display: inline-block;
        background: #EEF2FF;
        color: #3730A3;
        border-radius: 20px;
        padding: 0.25rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .disclaimer-box {
        background: #F1F5F9;
        border-left: 4px solid #94A3B8;
        padding: 1rem 1.25rem;
        border-radius: 0 8px 8px 0;
        color: #64748B;
        font-size: 0.85rem;
        line-height: 1.5;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="agent-header">
        <h1>AI Lending Decision Support</h1>
        <p>Powered by LangGraph · FAISS RAG · Llama 3.1 · Responsible AI</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    This agent autonomously analyzes borrower profiles using three ML models, retrieves relevant
    regulatory guidelines (RBI, Basel III, CIBIL), and generates a structured credit assessment report.
    """)

    # LangGraph Workflow Visualization
    with st.expander("Explore LangGraph Orchestration Logic", expanded=True):
        st.markdown("#### Agentic State Machine")
        st.write(
            "The system is orchestrated using a stateful directed graph. Unlike a simple text-in-text-out LLM, "
            "this agent transitions through specific logic nodes while maintaining a persistent 'AgentState'."
        )
        
        col_wf1, col_wf2, col_wf3, col_wf4, col_wf5 = st.columns(5)
        
        with col_wf1:
            st.markdown("""
            <div style="background: #F1F5F9; border: 1px solid #CBD5E1; padding: 10px; border-radius: 8px; text-align: center; height: 160px;">
                <b style="color: #1E3A8A;">1. Parse</b><br>
                <small>Sanitizes input & standardizes profile metrics</small>
            </div>
            """, unsafe_allow_html=True)

        with col_wf2:
            st.markdown("""
            <div style="background: #F1F5F9; border: 1px solid #CBD5E1; padding: 10px; border-radius: 8px; text-align: center; height: 160px;">
                <b style="color: #1E3A8A;">2. ML Score</b><br>
                <small>Executes XGBoost M1 prediction engine</small>
            </div>
            """, unsafe_allow_html=True)

        with col_wf3:
            st.markdown("""
            <div style="background: #F1F5F9; border: 1px solid #CBD5E1; padding: 10px; border-radius: 8px; text-align: center; height: 160px;">
                <b style="color: #1E3A8A;">3. RAG</b><br>
                <small>Retrieves regulatory context via FAISS</small>
            </div>
            """, unsafe_allow_html=True)

        with col_wf4:
            st.markdown("""
            <div style="background: #F1F5F9; border: 1px solid #CBD5E1; padding: 10px; border-radius: 8px; text-align: center; height: 160px;">
                <b style="color: #1E3A8A;">4. Reason</b><br>
                <small>LLM synthesizes score + regulations</small>
            </div>
            """, unsafe_allow_html=True)

        with col_wf5:
            st.markdown("""
            <div style="background: #F1F5F9; border: 1px solid #CBD5E1; padding: 10px; border-radius: 8px; text-align: center; height: 160px;">
                <b style="color: #1E3A8A;">5. Format</b><br>
                <small>Generates structured JSON credit report</small>
            </div>
            """, unsafe_allow_html=True)

        st.info("Technical Detail: The agent uses **LangGraph's State Persistence** to ensure that data from late-stage nodes (like RAG) can be compared against early-stage nodes (like ML Scoring) for consistency.")

    st.markdown("---")
    st.subheader("Borrower Profile Input")

    with st.form("agent_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Personal Details**")
            age = st.number_input("Age", min_value=18, max_value=100, value=35, key="ag_age")
            gender = st.selectbox("Gender", ["male", "female"], key="ag_gender")
            education = st.selectbox(
                "Education",
                ['High School', 'Associate', 'Bachelor', 'Master', 'Doctorate'],
                index=2,
                key="ag_edu"
            )
            home_ownership = st.selectbox(
                "Home Ownership",
                df['person_home_ownership'].unique(),
                key="ag_home"
            )

        with col2:
            st.markdown("**Financial Details**")
            income = st.number_input("Annual Income (₹)", min_value=0, value=75000, step=1000, key="ag_income")
            employment_years = st.number_input(
                "Employment Experience (Years)", min_value=0, max_value=50, value=8, key="ag_emp"
            )
            credit_score = st.number_input("Credit Score", min_value=300, max_value=850, value=690, key="ag_cs")
            credit_history_years = st.number_input(
                "Credit History Length (Years)", min_value=0, max_value=50, value=7, key="ag_ch"
            )

        with col3:
            st.markdown("**Loan Details**")
            loan_amount = st.number_input("Loan Amount (₹)", min_value=100, value=15000, step=500, key="ag_la")
            loan_intent = st.selectbox("Loan Purpose", df['loan_intent'].unique(), key="ag_li")
            interest_rate = st.number_input(
                "Interest Rate (%)", min_value=0.0, max_value=30.0, value=11.5, step=0.1, key="ag_ir"
            )
            previous_defaults = st.selectbox("Previous Defaults on File", ["No", "Yes"], key="ag_pd")

        generate = st.form_submit_button(
            "Generate AI Assessment Report",
            use_container_width=True,
            type="primary",
            key="m2_agent_btn"
        )

    if generate:
        st.session_state.last_agent_run = None 
        borrower_profile = {
            "age": age,
            "gender": gender,
            "education": education,
            "home_ownership": home_ownership,
            "income": income,
            "employment_years": employment_years,
            "credit_score": credit_score,
            "credit_history_years": credit_history_years,
            "loan_amount": loan_amount,
            "loan_intent": loan_intent,
            "interest_rate": interest_rate,
            "previous_defaults": previous_defaults,
        }

        with st.spinner("Running AI agent — analyzing profile, retrieving regulations, generating report..."):
            try:
                agent_graph = get_agent_graph(lr_result, dt_result, xgb_result)
                initial_state = {
                    "borrower_profile": borrower_profile,
                    "ml_scores": {},
                    "risk_drivers": [],
                    "rag_context": [],
                    "assessment_report": {},
                    "error": None,
                }
                st.session_state.last_agent_run = agent_graph.invoke(initial_state)
            except Exception as e:
                st.error(f"Agent Execution Failed: {str(e)}")
                return

    if st.session_state.get("last_agent_run"):
        final_state = st.session_state.last_agent_run
        
        if final_state.get("error"):
            st.error(f"Agent Error: {final_state['error']}")
            return

        st.markdown("---")
        st.subheader("Structured Credit Assessment Report")

        st.markdown("**Agent Workflow Completed:**")
        for step in ["1. Parse Borrower Profile", "2. ML Risk Scoring", "3. RAG Regulation Retrieval", "4. LLM Assessment", "5. Report Formatting"]:
            st.markdown(f'<span class="step-badge">{step}</span>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        ml_scores = final_state.get("ml_scores", {})
        risk_drivers = final_state.get("risk_drivers", [])
        rag_context = final_state.get("rag_context", [])
        report = final_state.get("assessment_report", {})

        col_a, col_b, col_c = st.columns(3)
        risk_class = ml_scores.get("risk_class", "N/A")
        default_prob = ml_scores.get("consensus_default_probability", 0)
        model_probs = ml_scores.get("model_probabilities", {})

        with col_a:
            st.metric("XGBoost (Primary)", f"{default_prob:.1f}%", delta=None)
        with col_b:
            st.metric("Logistic Regression", f"{model_probs.get('Logistic Regression', 0):.1f}%")
        with col_c:
            st.metric("Decision Tree", f"{model_probs.get('Decision Tree', 0):.1f}%")

        if risk_class == "High Risk":
            st.error(f"Consensus Risk Classification: **{risk_class}**")
        elif risk_class == "Medium Risk":
            st.warning(f"Consensus Risk Classification: **{risk_class}**")
        else:
            st.success(f"Consensus Risk Classification: **{risk_class}**")

        if risk_drivers:
            st.markdown(f"**Top Risk Drivers:** {' · '.join(risk_drivers)}")

        st.markdown("<br>", unsafe_allow_html=True)

        if "error" in report:
            st.error("LLM report generation failed. Raw output shown below.")
            st.code(report.get("raw_output", "No output available"))
            return

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("""
            <div class="report-card">
                <h3>Borrower Summary</h3>
            </div>
            """, unsafe_allow_html=True)
            st.write(report.get("borrower_summary", "N/A"))

            st.markdown("""
            <div class="report-card" style="margin-top:1rem;">
                <h3>Risk Analysis</h3>
            </div>
            """, unsafe_allow_html=True)
            st.write(report.get("risk_analysis", "N/A"))

        with col_right:
            decision = report.get("lending_decision", "N/A")
            if decision == "APPROVE":
                decision_class = "decision-approve"
                decision_icon = ""
            elif decision == "CONDITIONAL APPROVE":
                decision_class = "decision-conditional"
                decision_icon = "️"
            else:
                decision_class = "decision-decline"
                decision_icon = ""

            st.markdown(f"""
            <div class="report-card {decision_class}">
                <h3>{decision_icon} Lending Decision: {decision}</h3>
            </div>
            """, unsafe_allow_html=True)
            st.write(report.get("decision_rationale", "N/A"))

            conditions = report.get("conditions", [])
            if conditions:
                st.markdown("**Conditions:**")
                for cond in conditions:
                    st.markdown(f"- {cond}")

        st.markdown("---")

        col_reg, col_rai = st.columns(2)

        with col_reg:
            st.markdown("#### Regulatory References")
            refs = report.get("regulatory_references", [])
            if refs:
                for ref in refs:
                    st.markdown(f"- {ref}")
            else:
                st.write("No specific regulatory references cited.")

            with st.expander("Retrieved Regulation Chunks"):
                for i, chunk in enumerate(rag_context, 1):
                    st.markdown(f"**Source {i}: {chunk.get('source', 'Unknown')}** (score: {chunk.get('score', 0):.3f})")
                    st.write(chunk.get('text', '')[:300] + "…")
                    st.markdown("---")

        with col_rai:
            st.markdown("#### Responsible AI")
            st.info(report.get("responsible_ai_note", "This assessment adheres to fair lending principles."))

        st.markdown("---")
        st.markdown("####️ Legal Disclaimer")
        st.markdown(
            f'<div class="disclaimer-box">{report.get("disclaimer", "This AI-generated assessment is for informational purposes only and does not constitute a final lending decision.")}</div>',
            unsafe_allow_html=True
        )


def _render_dataset_page():
    st.title("Dataset Information")
    st.write(
        "This project uses a loan default prediction dataset. It contains demographics, "
        "financial information, and loan details to determine the likelihood of default."
    )
    st.markdown("### Data Source")
    st.write("The dataset is sourced from historical lending data and reflects real-world scenarios in finance and risk assessment.")

    st.markdown("### Sample Data")
    st.dataframe(df.head(100), use_container_width=True)

    st.markdown("### Features Summary")
    st.write("A statistical summary of the quantitative characteristics included in the dataset.")
    st.dataframe(df.describe(), use_container_width=True)


def _render_model_comparison_page():
    st.title("Detailed Model Comparison")
    st.write(
        "Below is a detailed breakdown of each model's performance, allowing you to compare "
        "accuracy, F1-scores, ROC curves, and prediction results via confusion matrices."
    )

    models_info = [
        ("Logistic Regression", lr_model, lr_X_test, lr_y_test, lr_scaler, '#5b9bd5'),
        ("Decision Tree", dt_model, dt_X_test, dt_y_test, None, '#ed7d31'),
        ("XGBoost", xgb_model, xgb_X_test, xgb_y_test, None, '#ffc000'),
    ]

    for name, model, X_t, y_t, scaler, color in models_info:
        st.markdown(f"### {name}")

        X_t_scaled = scaler.transform(X_t) if scaler is not None else X_t
        y_pred = model.predict(X_t_scaled)
        y_prob = model.predict_proba(X_t_scaled)[:, 1]

        acc = accuracy_score(y_t, y_pred)
        f1 = f1_score(y_t, y_pred)
        auc = roc_auc_score(y_t, y_prob)

        col1, col2, col3 = st.columns(3)
        col1.metric("Accuracy", f"{acc * 100:.2f}%")
        col2.metric("F1 Score", f"{f1:.4f}")
        col3.metric("ROC AUC", f"{auc:.4f}")

        col_cm, col_roc = st.columns(2)

        with col_cm:
            cm = confusion_matrix(y_t, y_pred)
            fig_cm, ax_cm = plt.subplots(figsize=(4, 3))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False, ax=ax_cm)
            ax_cm.set_xlabel('Predicted Label')
            ax_cm.set_ylabel('True Label')
            ax_cm.set_title('Confusion Matrix')
            plt.tight_layout()
            st.pyplot(fig_cm)

        with col_roc:
            fpr, tpr, _ = roc_curve(y_t, y_prob)
            fig_roc, ax_roc = plt.subplots(figsize=(4, 3))
            ax_roc.plot(fpr, tpr, color=color, linewidth=2, label=f'AUC = {auc:.3f}')
            ax_roc.plot([0, 1], [0, 1], color='#cccccc', linestyle='--')
            ax_roc.set_xlabel('False Positive Rate')
            ax_roc.set_ylabel('True Positive Rate')
            ax_roc.set_title('ROC Curve')
            ax_roc.legend(loc='lower right')
            plt.tight_layout()
            st.pyplot(fig_roc)

        st.markdown("---")


def _render_architecture_page():
    st.title("System Architecture")
    st.write("High-level architecture of the Credit Risk AI system covering both Milestone 1 and Milestone 2.")

    st.markdown("### Milestone 1 — ML Pipeline")
    st.markdown(
        "1. **Data Ingestion**: Application loads historic demographic and loan behavioral data (`loan_data.csv`).\n"
        "2. **Data Preprocessing**: Cleaning, handling missing values, encoding categoricals, and applying Standard Scalers where required.\n"
        "3. **Model Training**: Constructing pipelines using algorithms suitable for binary classification (Logistic Regression, Decision Trees, XGBoost).\n"
        "4. **Dashboard**: An interactive Streamlit UI for real-time inference, model comparison, and risk classification.\n"
    )

    st.markdown("### Milestone 2 — Agentic AI Extension")
    st.markdown(
        "1. **LangGraph Agent**: Five-node workflow (Parse → ML Score → RAG Retrieve → LLM Assess → Format Report).\n"
        "2. **FAISS RAG**: TF-IDF vectors stored in a FAISS index over three regulation corpora (RBI, Basel III, CIBIL).\n"
        "3. **Groq LLM (Llama 3.1)**: Generates structured 4-section JSON credit reports grounded in retrieved regulations.\n"
        "4. **Responsible AI**: Protected attributes excluded; structured output constrains hallucinations; sources cited.\n"
    )

    st.markdown("---")
    st.image("assets/milestone2_architecture_detailed.png", use_container_width=True, caption="Detailed End-to-End System Architecture")


def _render_report_page():
    st.title("Project Report")
    st.link_button(
        "View Report on Google Drive",
        "https://drive.google.com/file/d/1SO0Pme8BG06E0wikFb77NZ8G2HPcwc49/view?usp=sharing",
        use_container_width=True
    )
    st.markdown("Below is the formal project report detailing our approach and methodology.")

    import os
    import base64

    report_path = "reports/loan_risk_report.pdf"
    if os.path.exists(report_path):
        with open(report_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.info("The project report PDF is not currently loaded in the directory. Please upload 'loan_risk_report.pdf' to view it here.")


if __name__ == "__main__":
    main()
