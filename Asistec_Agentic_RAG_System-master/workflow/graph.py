from functools import lru_cache

from langgraph.graph import START, StateGraph

from workflow.state import WorkflowState
from workflow.nodes import (
    answer_or_retrieve,
    generate_answer,
    retrieve,
    rewrite_query,
    score_documents,
    handle_memories,
    summarization_node,
)

@lru_cache(maxsize=1)
def create_graph() -> StateGraph:
    graph = (
        StateGraph(WorkflowState)
        .add_node(handle_memories)
        .add_node("summarize_messages", summarization_node)
        .add_node(answer_or_retrieve)
        .add_node(retrieve)
        .add_node(score_documents)
        .add_node(rewrite_query)
        .add_node(generate_answer)
    )

    # Edges
    graph.add_edge(START, "summarize_messages")
    graph.add_edge(START, "handle_memories")
    graph.add_edge("summarize_messages", "answer_or_retrieve")
    graph.add_edge("retrieve", "score_documents")

    return graph

# Compiled the graph
graph = create_graph().compile()