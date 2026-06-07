from typing import Literal
from pydantic import BaseModel, Field

from langchain_core.runnables import RunnableConfig
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage

from langmem.short_term import SummarizationNode
from langgraph.types import Command

from .state import WorkflowState
from .llms import summarization_model, main_model, scoring_model, rewriter_model
from .tools import tools, tools_by_name
from .prompts import (
    QUERY_ROUTER_MODEL_PROMPT,
    EXPERT_RESPONSE_MODEL_PROMPT,
    REWRITE_PROMPT,
    SCORE_PROMPT,
)
from core.mem0_client import mem0_client as memory
from core.config import settings

###########################
# Handle User Memories
###########################
def handle_memories(
    state: WorkflowState, 
    config: RunnableConfig
) -> Command[Literal["answer_or_retrieve"]]:
    """Handle the memories in the workflow state."""
    
    user_id = state["user_id"]
    message = state["messages"][-1].content

    memories = []
    
    # Insert memories from user's last message
    memory.add(message, user_id=user_id, version="v2")
    
    # Search user memories based on the last message
    results = memory.search(
        query=message,
        version="v2",
        filters={
            "AND": [
                {"user_id": user_id}
            ]
        }
    )
    for result in results:
        memories.append(result["memory"])

    return Command(
        goto="answer_or_retrieve",
        update={"memories": memories}
    )

###########################
# Summarize Messages
###########################
summarization_node = SummarizationNode(  
    token_counter=count_tokens_approximately,
    model=summarization_model,
    max_tokens=settings.MAX_TOKENS,
    max_tokens_before_summary=settings.MESSAGES_SUMMARY_TRIGGER,
    max_summary_tokens=settings.MAX_SUMMARY_TOKENS, 
    input_messages_key="messages",
    output_messages_key="messages",
    name="summarize_messages"
)

###########################
# Answer or Retrieve
###########################
def answer_or_retrieve(
    state: WorkflowState, config: RunnableConfig
) -> Command[Literal["retrieve", "__end__"]]:
    """Decide whether to answer or retrieve documents."""
    messages = state["messages"]

    # Format user memories for prompt injection
    memories = state["memories"]
    if memories:
        user_memories = "User Memories:\n" + "\n".join(f"- {m}" for m in memories)
    else:
        user_memories = "User Memories: (no memories yet)"

    agent_with_tool = main_model.bind_tools(tools)
    response = agent_with_tool.invoke(
        [
            SystemMessage(
                content=QUERY_ROUTER_MODEL_PROMPT.format(memories=user_memories)
            )
        ] + messages
    )

    if hasattr(response, "tool_calls") and response.tool_calls:
        return Command(
            goto="retrieve", update={"messages": [response]}
        )
    # End the conversation
    return Command(update={"messages": [response]}, goto="__end__")

###########################
# Retrieval Node
###########################
def retrieve(
    state: WorkflowState, config: RunnableConfig
) -> Command[Literal["score_documents"]]:
    """Retrieve documents based on the last message's tool call."""

    results = ""
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        result: str = tool.invoke(tool_call["args"])
        if result:
            results += f"---\n{result}\n---"

    return Command(
        update={"context": results},
        goto="score_documents"
    )

###########################
# Score Documents
###########################
class ScoreDocument(BaseModel):
    score: int = Field(..., description="Score for the documents (combined) from 1-10 for a given query.", ge=1, le=10)

def score_documents(
    state: WorkflowState, config: RunnableConfig
) -> Command[Literal["rewrite_query", "generate_answer"]]:
    """Score the retrieved documents and route accordingly."""

    last_ai_message = state["messages"][-1]  # AIMessage with tool call
    question = state["messages"][0].content  # HumanMessage
    docs = state["context"]
    loop_count = state["retrieval_loop_count"]

    prompt = SCORE_PROMPT.format(question=question, docs=docs)
    
    response = (
        scoring_model
        .with_structured_output(ScoreDocument)
        .invoke([HumanMessage(content=prompt)])
    )

    if (
        response.score < settings.SCORE_THRESHOLD
        and loop_count < settings.MAX_RETRIEVAL_LOOP_COUNT
    ):
        return Command(
            goto="rewrite_query", update={"retrieval_loop_count": loop_count + 1}
        )
    else:
        delete_ai_message = RemoveMessage(id=last_ai_message.id)
        return Command(goto="generate_answer", update={"messages": [delete_ai_message]})

###########################
# Rewrite Query
###########################
class ModifiedQuery(BaseModel):
    query: str = Field(..., description="The enhanced query in Spanish to search into the vector store.")


def rewrite_query(
    state: WorkflowState, config: RunnableConfig
) -> Command[Literal["retrieve"]]:
    """Rewrite the original user question."""

    ai_message = state["messages"][-1]
    tool_call = ai_message.tool_calls[-1]

    prompt = REWRITE_PROMPT.format(query=tool_call["args"]["query"])
    response = (
        rewriter_model
        .with_structured_output(ModifiedQuery)
        .invoke([HumanMessage(content=prompt)])
    )

    # Update the tool call
    updated_message = {
        "role": "ai",
        "content": ai_message.content,
        "tool_calls": [
            {
                "id": tool_call["id"],
                "name": tool_call["name"],
                "args": {"query": response.query},
            }
        ],
        "id": ai_message.id,
    }

    return Command(goto="retrieve", update={"messages": [updated_message]})

###########################
# Generate Final Answer
###########################
def generate_answer(
    state: WorkflowState, config: RunnableConfig
) -> Command[Literal["__end__"]]:
    """Generate final answer"""

    messages = state["messages"]
    context = state["context"]
    memories = state["memories"]

    # Format user memories for prompt injection
    if memories:
        user_memories = "User Memories:\n" + "\n".join(f"- {m}" for m in memories)
    else:
        user_memories = "User Memories: (no memories yet)"

    response = main_model.invoke(
        [
            SystemMessage(
                content=EXPERT_RESPONSE_MODEL_PROMPT.format(
                    memories=user_memories, context=context
                )
            )
        ] + messages
    )

    # End the conversation
    return Command(update={"messages": [response]}, goto="__end__")
