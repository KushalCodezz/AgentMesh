"""
agents/base.py — Base Agent class.
All specialist agents inherit from this. Provides:
- Common interface for execute()
- Reliability scoring (historical accuracy)
- Provenance ref creation
- Structured logging
"""
from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.envelope import AgentResult, CapabilityTag, ProvenanceRef, TaskSpec

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base for all AI Office agents.
    
    Subclasses must implement:
    - agent_id: str  (e.g. "product_manager_agent")
    - capabilities: list[CapabilityTag]
    - _execute(task: TaskSpec) -> AgentResult
    """

    agent_id: str = "base_agent"
    capabilities: List[CapabilityTag] = []
    model_preference: str = "claude"

    def __init__(self):
        self._history: List[AgentResult] = []
        self._reliability_score: float = 1.0

    @abstractmethod
    async def _execute(self, task: TaskSpec) -> AgentResult:
        """Core execution logic — override in each specialist agent."""
        ...

    async def execute(self, task: TaskSpec) -> AgentResult:
        """
        Public execute interface. Wraps _execute with:
        - Timing
        - Reliability tracking
        - Error handling
        """
        start = time.monotonic()
        try:
            result = await self._execute(task)
            result.latency_ms = int((time.monotonic() - start) * 1000)
            self._record_outcome(result)
            return result
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error(f"[{self.agent_id}] Error on task {task.task_id}: {e}", exc_info=True)
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                output={},
                confidence=0.0,
                latency_ms=latency_ms,
                error=str(e),
            )
            self._record_outcome(result)
            return result

    def _record_outcome(self, result: AgentResult) -> None:
        """Update rolling reliability score based on success/failure."""
        self._history.append(result)
        # Keep last 50 results
        if len(self._history) > 50:
            self._history = self._history[-50:]

        # Exponential moving average of success
        alpha = 0.1
        success_val = 1.0 if result.success else 0.0
        self._reliability_score = (
            alpha * success_val + (1 - alpha) * self._reliability_score
        )

    @property
    def reliability_score(self) -> float:
        return round(self._reliability_score, 3)

    def make_ref(
        self,
        ref_type: str,
        ref_id: str,
        description: str = "",
        source_url: str = "",
    ) -> ProvenanceRef:
        return ProvenanceRef(
            ref_type=ref_type,
            ref_id=ref_id,
            description=description,
            source_url=source_url,
        )

    def get_stats(self) -> Dict[str, Any]:
        recent = self._history[-20:] if self._history else []
        return {
            "agent_id": self.agent_id,
            "reliability_score": self.reliability_score,
            "total_tasks": len(self._history),
            "recent_success_rate": (
                sum(1 for r in recent if r.success) / len(recent) if recent else 0
            ),
            "avg_confidence": (
                sum(r.confidence for r in recent) / len(recent) if recent else 0
            ),
            "avg_latency_ms": (
                sum(r.latency_ms for r in recent) / len(recent) if recent else 0
            ),
        }
