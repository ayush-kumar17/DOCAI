"""
RAG Agent — assembles the LangGraph and exposes run().

The graph is compiled once and reused for all requests.
Compiling is expensive; running is fast.
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
from langgraph.graph import StateGraph, END

from services.agent.state import AgentState
from services.agent.nodes import (
    router_node,
    retrieve_node,
    generate_node,
    refine_query_node,
    should_refine,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Compiled graph — built once at module load
_graph = None


def get_graph():
    """Build and compile the LangGraph. Cached after first call."""
    global _graph

    if _graph is not None:
        return _graph

    logger.info("Building LangGraph agent")

    builder = StateGraph(AgentState)

    # ── Add nodes ─────────────────────────────
    builder.add_node("router",       router_node)
    builder.add_node("retrieve",     retrieve_node)
    builder.add_node("generate",     generate_node)
    builder.add_node("refine_query", refine_query_node)

    # ── Add edges ─────────────────────────────
    # Entry point
    builder.set_entry_point("router")

    # router always goes to retrieve
    builder.add_edge("router", "retrieve")

    # retrieve always goes to generate
    builder.add_edge("retrieve", "generate")

    # After generate: decide whether to refine or finish
    builder.add_conditional_edges(
        "generate",
        should_refine,
        {
            "refine": "refine_query",
            "done":   END,
        },
    )

    # After refining: go back to retrieve
    builder.add_edge("refine_query", "retrieve")

    # ── Compile ───────────────────────────────
    _graph = builder.compile()
    logger.info("LangGraph agent compiled")

    return _graph


class RAGAgent:
    """
    High-level interface to the RAG agent.

    Usage:
        agent  = RAGAgent()
        result = await agent.run(query, doc_ids, owner_id, history)
    """

    def __init__(self):
        self.graph = get_graph()

    async def run(
        self,
        query:    str,
        doc_ids:  List[str],
        owner_id: str,
        history:  List[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Run the agent and return the complete result.

        Returns:
        {
            "answer":      "...",
            "citations":   [...],
            "intent":      "qa",
            "confidence":  0.87,
            "chunks_used": 5,
            "iterations":  1,
        }
        """
        initial_state: AgentState = {
            "query":             query,
            "doc_ids":           doc_ids,
            "owner_id":          owner_id,
            "history":           history or [],
            "intent":            "qa",
            "retrieval_queries": [query],
            "chunks":            [],
            "answer":            "",
            "citations":         [],
            "confidence":        0.0,
            "iteration":         0,
        }

        logger.info(
            "Agent run started",
            query    = query[:80],
            doc_ids  = doc_ids,
            owner_id = owner_id,
        )

        final_state = await self.graph.ainvoke(initial_state)

        result = {
            "answer":      final_state["answer"],
            "citations":   final_state["citations"],
            "intent":      final_state["intent"],
            "confidence":  final_state["confidence"],
            "chunks_used": len(final_state["chunks"]),
            "iterations":  final_state["iteration"],
        }

        logger.info(
            "Agent run complete",
            intent     = result["intent"],
            confidence = result["confidence"],
            chunks_used= result["chunks_used"],
            iterations = result["iterations"],
        )

        return result

    async def stream(
        self,
        query:    str,
        doc_ids:  List[str],
        owner_id: str,
        history:  List[Dict] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream agent events as they happen.

        Yields dicts with type:
            {"type": "intent",    "data": "qa"}
            {"type": "chunks",    "data": 5}
            {"type": "token",     "data": "The answer is..."}
            {"type": "citations", "data": [...]}
            {"type": "done",      "data": {"confidence": 0.87}}

        Note: true token streaming requires LangChain streaming callbacks.
        This version streams at the node level — you see events as each
        node completes. Token-level streaming is added in Phase 6 chat routes.
        """
        initial_state: AgentState = {
            "query":             query,
            "doc_ids":           doc_ids,
            "owner_id":          owner_id,
            "history":           history or [],
            "intent":            "qa",
            "retrieval_queries": [query],
            "chunks":            [],
            "answer":            "",
            "citations":         [],
            "confidence":        0.0,
            "iteration":         0,
        }

        async for event in self.graph.astream_events(
            initial_state,
            version="v1",
        ):
            event_name = event.get("name", "")
            event_type = event.get("event", "")

            # Node completed events
            if event_type == "on_chain_end":

                if event_name == "router":
                    output = event.get("data", {}).get("output", {})
                    yield {
                        "type": "intent",
                        "data": output.get("intent", "qa"),
                    }

                elif event_name == "retrieve":
                    output = event.get("data", {}).get("output", {})
                    chunks = output.get("chunks", [])
                    yield {
                        "type": "chunks",
                        "data": len(chunks),
                    }

                elif event_name == "generate":
                    output     = event.get("data", {}).get("output", {})
                    answer     = output.get("answer", "")
                    citations  = output.get("citations", [])
                    confidence = output.get("confidence", 0.0)

                    # Stream answer word by word
                    words = answer.split(" ")
                    for i, word in enumerate(words):
                        token = word + (" " if i < len(words) - 1 else "")
                        yield {"type": "token", "data": token}

                    yield {"type": "citations", "data": citations}
                    yield {
                        "type": "done",
                        "data": {"confidence": confidence},
                    }

                elif event_name == "refine_query":
                    yield {"type": "refining", "data": "Improving query..."}