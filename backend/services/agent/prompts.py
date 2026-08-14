"""
All prompts in one place.

Keeping prompts separate from logic means:
- Easy to iterate on prompt quality
- Easy to A/B test different prompts
- Clean separation of concerns
"""


ROUTER_PROMPT = """You are classifying a user's question about documents.

Classify the question into exactly one of these intents:
- qa:        A factual question with a specific answer
- compare:   Comparing information across documents or sections
- summarize: Asking for a summary of content
- extract:   Extracting specific data (dates, names, tables, lists)

Examples:
- "What is the main argument?" → qa
- "Compare the two reports" → compare
- "Summarize chapter 3" → summarize
- "List all the deadlines" → extract
- "What revenue was reported?" → extract

User question: {query}

Respond with ONLY the intent label, nothing else.
Valid responses: qa, compare, summarize, extract"""


ANSWER_PROMPT = """You are an expert document analyst helping users find information in their documents.

STRICT RULES:
1. Answer ONLY from the provided context — never from general knowledge
2. Every factual claim must have a citation like [Page X] or [Page X, Doc: Y]
3. If the answer is not in the context, say exactly: "I could not find this information in the provided documents."
4. Be precise and specific — avoid vague answers
5. For tables or structured data, preserve the structure in your answer

{history_section}

RETRIEVED CONTEXT:
{context}

USER QUESTION: {query}

Provide your answer below. Include inline citations for every claim.
At the end, write CONFIDENCE: X.X where X.X is your confidence from 0.0 to 1.0
that the context fully answers the question.

Answer:"""


COMPARE_PROMPT = """You are comparing information across multiple documents.

STRICT RULES:
1. Only use information from the provided context
2. Cite every claim with [Page X, Doc: Y]
3. Structure your comparison clearly with similarities and differences
4. If a document doesn't address a point, say so explicitly

{history_section}

RETRIEVED CONTEXT FROM EACH DOCUMENT:
{context}

USER QUESTION: {query}

Provide a structured comparison with citations.
At the end write CONFIDENCE: X.X

Answer:"""


SUMMARIZE_PROMPT = """You are summarizing document content for a user.

STRICT RULES:
1. Only summarize what is in the provided context
2. Preserve key facts, numbers, and conclusions
3. Cite page numbers for major points [Page X]
4. Structure with clear sections if the content has them

{history_section}

CONTENT TO SUMMARIZE:
{context}

USER REQUEST: {query}

Provide a well-structured summary with page citations.
At the end write CONFIDENCE: X.X

Summary:"""


EXTRACT_PROMPT = """You are extracting specific information from documents.

STRICT RULES:
1. Extract ONLY what is explicitly stated in the context
2. Present extracted data in a clear, structured format
3. Include exact page references for every extracted item [Page X]
4. If the requested information is not found, say so clearly

{history_section}

DOCUMENT CONTEXT:
{context}

EXTRACTION REQUEST: {query}

Extract the requested information with page citations.
At the end write CONFIDENCE: X.X

Extracted information:"""


REFINE_QUERY_PROMPT = """The initial retrieval for this question did not return confident results.

Original question: {query}
Initial answer confidence: {confidence}

Rewrite the question to be more specific and likely to match the document content.
Consider:
- Using different keywords
- Breaking the question into a more specific sub-question
- Focusing on the core information needed

Respond with ONLY the rewritten question, nothing else."""


def get_answer_prompt(intent: str) -> str:
    """Return the right prompt template for the given intent."""
    prompts = {
        "qa":        ANSWER_PROMPT,
        "compare":   COMPARE_PROMPT,
        "summarize": SUMMARIZE_PROMPT,
        "extract":   EXTRACT_PROMPT,
    }
    return prompts.get(intent, ANSWER_PROMPT)