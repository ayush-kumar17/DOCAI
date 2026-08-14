"""
Agent State

TypedDict that flows through every node in the LangGraph.
Each node reads from it and returns updated fields.
Think of it as the agent's working memory for one request.
"""

from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    # ── Input ─────────────────────────────────
    query:    str              # original user question
    doc_ids:  List[str]        # documents to search in
    owner_id: str              # current user id
    history:  List[Dict]       # prior messages [{role, content}]

    # ── Routing ───────────────────────────────
    intent:            str         # qa | compare | summarize | extract
    retrieval_queries: List[str]   # one query per doc for compare intent
                                   # single query for everything else

    # ── Retrieval ─────────────────────────────
    chunks: List[Dict[str, Any]]   # retrieved + reranked chunks

    # ── Generation ────────────────────────────
    answer:     str
    citations:  List[Dict[str, Any]]
    confidence: float

    # ── Loop control ──────────────────────────
    iteration: int   # how many times we've refined the query
                     # stops infinite loops