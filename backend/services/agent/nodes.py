"""
LangGraph Node Implementations

Each node is an async function that:
- Receives the full AgentState
- Does one job
- Returns a dict of fields to update in the state

Nodes never modify state directly — they return updates.
LangGraph merges the updates into the state.
"""

import re
from typing import Dict, Any, List

from langchain_core.messages import SystemMessage, HumanMessage

from services.retrieval.hybrid_retriever import HybridRetriever
from services.agent.prompts import (
    ROUTER_PROMPT,
    REFINE_QUERY_PROMPT,
    get_answer_prompt,
)
from services.agent.llm import get_llm
from services.agent.state import AgentState
from utils.logger import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Node 1: Router
# ──────────────────────────────────────────────

async def router_node(state: AgentState) -> Dict[str, Any]:
    """
    Classify the user's intent and set up retrieval queries.

    For 'compare' with multiple docs:
        Build one query per document so we retrieve
        relevant chunks from each separately.

    For everything else:
        Use the original query directly.
    """
    llm = get_llm()

    prompt   = ROUTER_PROMPT.format(query=state["query"])
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    intent   = response.content.strip().lower()

    # Validate — default to "qa" if model returns something unexpected
    if intent not in ("qa", "compare", "summarize", "extract"):
        logger.warning(f"Unknown intent '{intent}', defaulting to 'qa'")
        intent = "qa"

    logger.info(f"Intent classified: {intent}")

    # For compare: one query per document
    retrieval_queries = [state["query"]]
    if intent == "compare" and len(state.get("doc_ids", [])) > 1:
        retrieval_queries = [
            f"In this document: {state['query']}"
            for _ in state["doc_ids"]
        ]

    return {
        "intent":            intent,
        "retrieval_queries": retrieval_queries,
        "iteration":         0,
    }


# ──────────────────────────────────────────────
# Node 2: Retrieve
# ──────────────────────────────────────────────

async def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """
    Run hybrid retrieval for each query in retrieval_queries.

    For compare intent: retrieve from each doc separately.
    For everything else: single retrieval pass.
    """
    retriever = HybridRetriever()
    intent    = state.get("intent", "qa")
    doc_ids   = state.get("doc_ids", [])
    owner_id  = state.get("owner_id", "")

    all_chunks: List[Dict] = []

    if intent == "compare" and len(doc_ids) > 1:
        # Retrieve top chunks from each document separately
        for doc_id, query in zip(doc_ids, state["retrieval_queries"]):
            chunks = await retriever.retrieve(
                query    = query,
                doc_ids  = [doc_id],
                owner_id = owner_id,
                top_k    = 3,    # 3 chunks per document
            )
            # Tag which document these came from
            for chunk in chunks:
                chunk["source_doc"] = doc_id
            all_chunks.extend(chunks)

    elif intent == "summarize":
        # For summarization, get more chunks to cover the full document
        all_chunks = await retriever.retrieve(
            query    = state["query"],
            doc_ids  = doc_ids or None,
            owner_id = owner_id,
            top_k    = 10,
        )

    else:
        # qa / extract — standard retrieval
        all_chunks = await retriever.retrieve(
            query    = state["retrieval_queries"][0],
            doc_ids  = doc_ids or None,
            owner_id = owner_id,
            top_k    = 5,
        )

    logger.info(f"Retrieved {len(all_chunks)} chunks for intent={intent}")
    return {"chunks": all_chunks}


# ──────────────────────────────────────────────
# Node 3: Generate
# ──────────────────────────────────────────────

async def generate_node(state: AgentState) -> Dict[str, Any]:
    """
    Generate answer from retrieved chunks.

    Steps:
    1. Format context from chunks
    2. Format conversation history
    3. Pick the right prompt for the intent
    4. Call LLM
    5. Extract confidence score from response
    6. Build structured citations
    """
    llm     = get_llm()
    chunks  = state.get("chunks", [])
    intent  = state.get("intent", "qa")

    if not chunks:
        return {
            "answer":     "I could not find relevant information in the provided documents.",
            "citations":  [],
            "confidence": 0.0,
        }

    # ── Format context ────────────────────────
    context = _format_context(chunks)

    # ── Format history ────────────────────────
    history = state.get("history", [])
    history_section = _format_history(history)

    # ── Build prompt ──────────────────────────
    prompt_template = get_answer_prompt(intent)
    prompt = prompt_template.format(
        query           = state["query"],
        context         = context,
        history_section = history_section,
    )

    # ── Call LLM ─────────────────────────────
    system = SystemMessage(content=(
        "You are an expert document analyst. "
        "You answer questions strictly based on provided document context. "
        "You never make up information not present in the context."
    ))
    human  = HumanMessage(content=prompt)

    response = await llm.ainvoke([system, human])
    answer   = response.content

    # ── Extract confidence ────────────────────
    confidence = _extract_confidence(answer)

    # ── Build citations ───────────────────────
    citations = _build_citations(chunks)

    logger.info(
        "Generation complete",
        intent     = intent,
        confidence = confidence,
        chunks_used= len(chunks),
    )

    return {
        "answer":    answer,
        "citations": citations,
        "confidence": confidence,
    }


# ──────────────────────────────────────────────
# Node 4: Refine Query
# ──────────────────────────────────────────────

async def refine_query_node(state: AgentState) -> Dict[str, Any]:
    """
    When confidence is low, rewrite the query and try again.

    The LLM rewrites the query to be more specific
    and more likely to match actual document content.
    """
    llm = get_llm()

    prompt = REFINE_QUERY_PROMPT.format(
        query      = state["query"],
        confidence = state.get("confidence", 0.0),
    )

    response  = await llm.ainvoke([HumanMessage(content=prompt)])
    new_query = response.content.strip()

    logger.info(
        "Query refined",
        original = state["query"][:80],
        refined  = new_query[:80],
        iteration= state.get("iteration", 0) + 1,
    )

    return {
        "retrieval_queries": [new_query],
        "iteration":         state.get("iteration", 0) + 1,
    }


# ──────────────────────────────────────────────
# Conditional edge function
# ──────────────────────────────────────────────

def should_refine(state: AgentState) -> str:
    """
    Decide what to do after generation.

    If confidence is low AND we haven't retried too many times:
        → refine the query and retrieve again

    Otherwise:
        → we're done, return the answer
    """
    confidence = state.get("confidence", 1.0)
    iteration  = state.get("iteration", 0)

    # Low confidence threshold
    if confidence < 0.3 and iteration < 2:
        logger.info(
            f"Low confidence ({confidence}) — refining query (iteration {iteration + 1})"
        )
        return "refine"

    return "done"


# ──────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────

def _format_context(chunks: List[Dict]) -> str:
    """
    Format retrieved chunks into a readable context block.

    Each chunk is labeled with its source so the LLM
    knows where to cite from.
    """
    if not chunks:
        return "No relevant context found."

    parts = []
    for i, chunk in enumerate(chunks, start=1):
        doc_id  = chunk.get("doc_id", "unknown")
        page    = chunk.get("page", "?")
        section = chunk.get("section", "")

        header = f"[Source {i} | Page {page}"
        if section:
            header += f" | {section}"
        header += f" | Doc: {doc_id[:8]}...]"

        parts.append(f"{header}\n{chunk['text']}")

    return "\n\n---\n\n".join(parts)


def _format_history(history: List[Dict]) -> str:
    """
    Format conversation history for the prompt.
    Only include the last 6 messages (3 turns) to stay within context limits.
    """
    if not history:
        return ""

    recent = history[-6:]
    lines  = ["CONVERSATION HISTORY (for context):"]

    for msg in recent:
        role    = msg.get("role", "user").upper()
        content = msg.get("content", "")
        # Truncate very long messages in history
        if len(content) > 500:
            content = content[:500] + "..."
        lines.append(f"{role}: {content}")

    return "\n".join(lines) + "\n\n"


def _extract_confidence(answer_text: str) -> float:
    """
    Extract the CONFIDENCE: X.X value the LLM writes at the end.
    Returns 0.7 as default if not found.
    """
    match = re.search(
        r"CONFIDENCE:\s*([0-9]+\.?[0-9]*)",
        answer_text,
        re.IGNORECASE,
    )
    if match:
        try:
            score = float(match.group(1))
            # Clamp to 0-1 range
            return max(0.0, min(1.0, score))
        except ValueError:
            pass

    return 0.7   # default if not found


def _build_citations(chunks: List[Dict]) -> List[Dict]:
    """
    Build structured citation objects from retrieved chunks.
    These are attached to the message and shown in the UI.
    """
    citations = []

    for chunk in chunks:
        citations.append({
            "doc_id":       chunk.get("doc_id", ""),
            "page":         chunk.get("page"),
            "section":      chunk.get("section", ""),
            "confidence":   chunk.get("confidence", 0.5),
            "text_snippet": chunk["text"][:300],    # first 300 chars
            "rerank_score": chunk.get("rerank_score", 0.0),
        })

    return citations