from pydantic import BaseModel, Field
from typing import Optional, Literal


class AnalysisRequest(BaseModel):
    """Request schema for financial analysis"""

    query: str = Field(..., min_length=10, max_length=1000)
    user_context: Optional[dict] = None
    reasoning_depth: Literal["standard", "deep"] = "standard"


class AnalysisResponse(BaseModel):
    """Response schema for starting analysis"""

    task_id: str
    status: str
    message: str


class AnalysisStatusResponse(BaseModel):
    """Response schema for analysis status"""

    task_id: str
    state: str  # PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
    status: Optional[str] = None
    message: Optional[str] = None
    progress: Optional[int] = None
    phase: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
