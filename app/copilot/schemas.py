"""
Pydantic schemas for SafeSight Copilot data contracts (Milestone 4).
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryPlan(BaseModel):
    intent: str = Field(..., description="visual | document | both | analytics | investigate | smalltalk | out_of_scope | needs_clarification")
    needs_visual: bool = Field(default=False)
    needs_document: bool = Field(default=False)
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities like zone, camera, violation_type, ppe_type, date_from, date_to, ids")
    rewritten_question: str = Field(default="", description="Stand-alone normalized English question")
    language: str = Field(default="en")
    confidence: float = Field(default=1.0)
    clarifying_question: Optional[str] = Field(default=None)


class KeyFact(BaseModel):
    label: str
    value: str
    cite: Optional[str] = None


class RecommendedAction(BaseModel):
    action: str
    cite: Optional[str] = None


class AnswerCard(BaseModel):
    headline: str = Field(..., max_length=120)
    answer: str = Field(..., description="Factual answer with citations like [V1] or [D2]")
    key_facts: List[KeyFact] = Field(default_factory=list)
    recommended_actions: List[RecommendedAction] = Field(default_factory=list)
    risk_level: str = Field(default="LOW", description="LOW | MEDIUM | HIGH | CRITICAL")
    follow_up_questions: List[str] = Field(default_factory=list)


class ValidationCheck(BaseModel):
    name: str
    passed: bool
    score: int
    reason: str


class ValidationReport(BaseModel):
    score: int = Field(..., ge=0, le=100)
    verdict: str = Field(..., description="pass | revise | fail")
    checks: List[ValidationCheck] = Field(default_factory=list)
    feedback: List[str] = Field(default_factory=list)


class FinalResponse(BaseModel):
    run_id: str
    question: str
    answer_card: AnswerCard
    visual_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    document_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    validation: ValidationReport
    route: List[str] = Field(default_factory=list)
    trace: List[Dict[str, Any]] = Field(default_factory=list)
    mode: str = Field(default="offline")
    confidence_label: str = Field(default="High")
    disclaimers: List[str] = Field(default_factory=list)
