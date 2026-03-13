"""
core/envelope.py — Canonical message envelope for all inter-agent communication.
Every message in the system uses this schema for traceability and provenance.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────

class MessageType(str, Enum):
    TASK = "task"
    REPLY = "reply"
    CRITIQUE = "critique"
    PROPOSAL = "proposal"
    EVENT = "event"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DEBATE = "debate"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class Priority(int, Enum):
    LOW = 10
    NORMAL = 50
    HIGH = 80
    CRITICAL = 100


class CapabilityTag(str, Enum):
    RESEARCH = "research"
    ARCHITECTURE = "architecture"
    CODE = "code"
    QA = "qa"
    CREATIVE = "creative"
    PLANNING = "planning"
    ADAPTIVE = "adaptive"
    DEBATE = "debate"


# ─── Sub-schemas ─────────────────────────────────────────────────────────────

class MessageMeta(BaseModel):
    deadline: Optional[datetime] = None
    priority: int = Priority.NORMAL
    budget_tokens: int = 4000
    requires_debate: bool = False
    requires_human_review: bool = False
    retry_count: int = 0
    max_retries: int = 3


class ProvenanceRef(BaseModel):
    """Reference to a stored artifact (vector or object store)."""
    ref_type: str  # "vector", "object", "url"
    ref_id: str
    description: Optional[str] = None
    source_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Evidence(BaseModel):
    claim: str
    source_url: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    ref: Optional[ProvenanceRef] = None


# ─── Core Envelope ───────────────────────────────────────────────────────────

class Envelope(BaseModel):
    """
    Canonical message envelope. All inter-agent messages use this schema.

    Fields:
        message_id    — Unique ID for this message
        trace_id      — Distributed trace ID (same across a full task chain)
        conversation_id — Groups all messages for a user conversation
        from_agent    — Sender agent ID or "orchestrator"
        to_agent      — Recipient agent ID or broadcast channel
        type          — MessageType enum
        payload       — Arbitrary typed dict (content depends on type)
        refs          — Provenance references (vector://, object://, url://)
        meta          — Scheduling metadata (deadline, budget, priority)
        timestamp     — UTC creation time
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = "orchestrator"
    to_agent: str = "broadcast"
    type: MessageType = MessageType.TASK
    payload: dict[str, Any] = Field(default_factory=dict)
    refs: List[ProvenanceRef] = Field(default_factory=list)
    meta: MessageMeta = Field(default_factory=MessageMeta)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def reply(self, from_agent: str, payload: dict, refs: List[ProvenanceRef] | None = None) -> "Envelope":
        """Create a reply envelope inheriting trace/conversation IDs."""
        return Envelope(
            trace_id=self.trace_id,
            conversation_id=self.conversation_id,
            from_agent=from_agent,
            to_agent=self.from_agent,
            type=MessageType.REPLY,
            payload=payload,
            refs=refs or [],
            meta=MessageMeta(
                priority=self.meta.priority,
                budget_tokens=self.meta.budget_tokens,
            ),
        )


# ─── Task Types ──────────────────────────────────────────────────────────────

class TaskSpec(BaseModel):
    """A discrete unit of work assigned to one or more agents."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    trace_id: str
    capability: CapabilityTag
    title: str
    description: str
    input_refs: List[ProvenanceRef] = Field(default_factory=list)
    assigned_agents: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: int = Priority.NORMAL
    budget_tokens: int = 4000
    deadline: Optional[datetime] = None
    depends_on: List[str] = Field(default_factory=list)  # task_ids
    result: Optional[dict] = None
    error: Optional[str] = None
    confidence: float = 0.0
    reliability_score: float = 1.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentResult(BaseModel):
    """Standardized result returned by any agent."""
    task_id: str
    agent_id: str
    success: bool
    output: dict[str, Any]
    refs: List[ProvenanceRef] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    tokens_used: int = 0
    latency_ms: int = 0
    error: Optional[str] = None
    requires_human_review: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
