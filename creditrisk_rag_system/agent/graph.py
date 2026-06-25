import functools
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import (
    parse_borrower_node,
    ml_scoring_node,
    rag_retrieval_node,
    llm_assessment_node,
    format_report_node,
)


def build_agent_graph(lr_result, dt_result, xgb_result):
    ml_node = functools.partial(
        ml_scoring_node,
        lr_result=lr_result,
        dt_result=dt_result,
        xgb_result=xgb_result,
    )

    graph = StateGraph(AgentState)
    graph.add_node("parse_borrower", parse_borrower_node)
    graph.add_node("ml_scoring", ml_node)
    graph.add_node("rag_retrieval", rag_retrieval_node)
    graph.add_node("llm_assessment", llm_assessment_node)
    graph.add_node("format_report", format_report_node)

    graph.set_entry_point("parse_borrower")
    graph.add_edge("parse_borrower", "ml_scoring")
    graph.add_edge("ml_scoring", "rag_retrieval")
    graph.add_edge("rag_retrieval", "llm_assessment")
    graph.add_edge("llm_assessment", "format_report")
    graph.add_edge("format_report", END)

    return graph.compile()
