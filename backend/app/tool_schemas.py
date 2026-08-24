from google.genai import types

SEARCH_DOCUMENTS = types.FunctionDeclaration(
    name="search_documents",
    description=(
        "Search policy documents, SOPs, product guides, and customer agreements. "
        "Use for any question about rules, fees, SLAs, coverage, or known issues. "
        "Results are ranked by source authority: signed customer agreement > current "
        "policy/SOP/product guide > deprecated policy (ranked last, do not treat as current)."
    ),
    parameters={
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "Natural-language search query."},
            "top_k": {"type": "INTEGER", "description": "Number of chunks to return (default 5)."},
        },
        "required": ["query"],
    },
)

QUERY_STRUCTURED_DATA = types.FunctionDeclaration(
    name="query_structured_data",
    description=(
        "Look up a specific order or ticket by ID, or run a calculation against one. "
        "Always scoped to the caller's own account unless the caller has an internal role."
    ),
    parameters={
        "type": "OBJECT",
        "properties": {
            "entity": {"type": "STRING", "enum": ["order", "ticket"]},
            "lookup_id": {"type": "STRING", "description": "e.g. ORD-1001 or TKT-501"},
            "calculation": {
                "type": "STRING",
                "enum": ["hours_late", "service_credit_amount", "cancellation_fee"],
                "description": "Optional calculation to run against the looked-up order.",
            },
        },
        "required": ["entity", "lookup_id"],
    },
)

CREATE_ESCALATION = types.FunctionDeclaration(
    name="create_escalation",
    description=(
        "Propose an escalation (e.g. to a human agent or manager) when policy doesn't cover "
        "the situation, sources conflict with no clear precedence, an exception is requested, "
        "or the request needs human judgment. This only drafts the escalation; it is never "
        "written until the user explicitly confirms in the UI."
    ),
    parameters={
        "type": "OBJECT",
        "properties": {
            "action_type": {"type": "STRING", "description": "e.g. 'manager_approval', 'support_escalation'"},
            "reason": {"type": "STRING", "description": "Why this needs escalation."},
            "summary": {"type": "STRING", "description": "One-line summary of what will happen."},
            "ticket_id": {"type": "STRING", "description": "Related ticket ID, if any."},
        },
        "required": ["action_type", "reason", "summary"],
    },
)

ALL_TOOLS = types.Tool(
    function_declarations=[SEARCH_DOCUMENTS, QUERY_STRUCTURED_DATA, CREATE_ESCALATION]
)

TOOL_NAMES = {"search_documents", "query_structured_data", "create_escalation"}
