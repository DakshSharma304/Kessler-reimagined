"""Document both existing 422 shapes; do not change exception behavior."""
from typing import Any,Literal
from pydantic import BaseModel,ConfigDict

class ScientificErrorResponse(BaseModel):
    status: Literal['NOT_FOUND','UNAVAILABLE','UNSUPPORTED','BUSY']
    detail: str

class ValidationIssue(BaseModel):
    model_config=ConfigDict(extra='allow')
    loc: list[str | int]
    msg: str
    type: str
    input: Any = None
    ctx: dict | None = None

class ValidationFailure(BaseModel):
    detail: list[ValidationIssue]

ERROR_RESPONSES={422:{'model':ScientificErrorResponse | ValidationFailure},
    404:{'model':ScientificErrorResponse},503:{'model':ScientificErrorResponse},429:{'model':ScientificErrorResponse}}
