from langgraph.graph import MessagesState

class WorkflowState(MessagesState):
    """Represents the state of the workflow."""
    user_id: str
    context: str
    memories: list[str]
    retrieval_loop_count: int = 0