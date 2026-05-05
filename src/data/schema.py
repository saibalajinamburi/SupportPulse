from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class Ticket(BaseModel):
    """Unified schema for support tickets across all data sources."""
    ticket_id: str
    source: Literal["github", "zendesk", "synthetic", "hf_customer_support", "kaggle_github_issues"]
    created_at: datetime
    subject: str
    body: str
    
    # Optional/Defaulted fields
    comments: List[str] = Field(default_factory=list)
    labels_raw: List[str] = Field(default_factory=list)
    
    # ML Prediction Targets
    category: Literal[
        "bug", "feature", "docs", "security", "performance", 
        "ui", "test", "dependency", "question", "incident"
    ]
    priority: Literal["critical", "high", "medium", "low"]
    routing_team: Literal["support", "engineering", "infra", "billing", "security"]
    
    # Metrics and Metadata
    sla_deadline: Optional[datetime] = None
    first_response_time: Optional[int] = None
    resolved_time: Optional[int] = None
    duplicate_of: Optional[str] = None
    
    customer_tier: Literal["free", "pro", "enterprise"] = "free"
    pii_flags: List[str] = Field(default_factory=list)
    reopen_count: int = 0

    class Config:
        from_attributes = True

class KBArticle(BaseModel):
    """Schema for Knowledge Base (KB) articles used in RAG retrieval."""
    article_id: str
    text: str
    source_url: str
    team_tag: str
    created_at: datetime
    confidence_level: str = "verified"

    class Config:
        from_attributes = True

class AgentTriageResult(BaseModel):
    """Schema for the final output of the agentic triage process."""
    ticket_id: str
    category: str
    priority: str
    routing_team: str
    
    category_confidence: float
    sla_risk_score: float
    breach_flag: bool
    
    duplicate_candidates: List[dict] = Field(default_factory=list)
    draft_response: Optional[dict] = None
    
    next_action: Literal[
        "ask_clarification", "draft_reply", "route", 
        "escalate", "mark_duplicate", "open_followup"
    ]
    next_action_reason: str
    
    mcp_tool_called: Optional[str] = None
    mcp_tool_result: Optional[dict] = None
    processing_time_ms: int

    class Config:
        from_attributes = True
