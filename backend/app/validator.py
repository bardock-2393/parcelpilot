"""Tool-call validator: schema check + forced account_id scoping.
Runs on every proposed tool call BEFORE it reaches the tool function -- the model's
own account_id (if any) is never trusted, and unknown params never reach the function."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from app.identity import Identity


class ValidationFailure(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class SearchDocumentsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    top_k: int = 5
    account_id: str | None = None


class QueryStructuredDataArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity: Literal["order", "ticket"]
    lookup_id: str
    calculation: Literal["hours_late", "service_credit_amount", "cancellation_fee"] | None = None
    account_id: str | None = None


class CreateEscalationArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: str
    reason: str
    summary: str
    ticket_id: str | None = None


SCHEMAS: dict[str, type[BaseModel]] = {
    "search_documents": SearchDocumentsArgs,
    "query_structured_data": QueryStructuredDataArgs,
    "create_escalation": CreateEscalationArgs,
}


def validate_call(tool_name: str, raw_args: dict[str, Any], identity: Identity) -> dict[str, Any]:
    """Validate + scope a proposed tool call. Raises ValidationFailure on bad input.
    Never trusts a model-supplied account_id: for customer sessions it is always
    forced to the session's real account_id; internal sessions may pass one through
    (or omit it, for cross-account reads)."""
    schema = SCHEMAS.get(tool_name)
    if schema is None:
        raise ValidationFailure(f"Unknown tool '{tool_name}'")
    try:
        parsed = schema(**raw_args)
    except ValidationError as exc:
        raise ValidationFailure(str(exc)) from exc

    args = parsed.model_dump()
    if "account_id" in args:
        if identity.is_internal:
            args["account_id"] = args.get("account_id") or None
        else:
            args["account_id"] = identity.account_id  # forced, ignoring whatever the model sent
    return args
