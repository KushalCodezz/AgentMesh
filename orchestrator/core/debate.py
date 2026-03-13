"""
core/debate.py — Multi-round Debate Engine.
Implements PROPOSE → CRITIQUE → RESPOND → AGGREGATE protocol.
Used for high-impact tasks to cross-validate agent outputs.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import anthropic

from core.envelope import AgentResult, TaskSpec

logger = logging.getLogger(__name__)


class DebatePhase(str, Enum):
    PROPOSE = "propose"
    CRITIQUE = "critique"
    RESPOND = "respond"
    AGGREGATE = "aggregate"
    DONE = "done"


@dataclass
class DebateProposal:
    agent_id: str
    proposal: dict
    evidence: List[dict] = field(default_factory=list)
    confidence: float = 0.8
    reliability_score: float = 1.0  # Historical accuracy weight
    round: int = 1


@dataclass
class DebateCritique:
    critic_agent_id: str
    target_agent_id: str
    issues: List[str] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)
    confidence: float = 0.8
    round: int = 1


@dataclass
class DebateState:
    task_id: str
    phase: DebatePhase = DebatePhase.PROPOSE
    round: int = 1
    max_rounds: int = 3
    proposals: List[DebateProposal] = field(default_factory=list)
    critiques: List[DebateCritique] = field(default_factory=list)
    final_result: Optional[dict] = None
    requires_human_review: bool = False
    history: List[dict] = field(default_factory=list)


AGGREGATOR_PROMPT = """You are a senior technical decision-maker. Given multiple agent proposals 
and critiques, produce the single best synthesized answer.

Rules:
1. Weight proposals by (confidence * reliability_score)
2. Incorporate valid critique points
3. Flag anything that requires human review (confidence < 0.6)
4. Return ONLY valid JSON:
{
  "final_output": { ... task-specific output ... },
  "confidence": 0.0-1.0,
  "reasoning": "why this is the best synthesis",
  "requires_human_review": false,
  "unresolved_issues": []
}"""


class DebateEngine:
    """
    Orchestrates multi-round structured debate between agents.
    
    Protocol:
    1. PROPOSE  — Each assigned agent submits a proposal with evidence
    2. CRITIQUE — Other agents critique each proposal  
    3. RESPOND  — Original proposers can revise based on critiques
    4. AGGREGATE — Compute weighted consensus; escalate if needed
    """

    def __init__(
        self,
        anthropic_api_key: str,
        confidence_threshold: float = 0.75,
        escalation_threshold: float = 0.60,
        max_rounds: int = 3,
    ):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.confidence_threshold = confidence_threshold
        self.escalation_threshold = escalation_threshold
        self.max_rounds = max_rounds

    def init_debate(self, task_id: str) -> DebateState:
        return DebateState(task_id=task_id, max_rounds=self.max_rounds)

    def add_proposal(
        self,
        state: DebateState,
        agent_id: str,
        proposal: dict,
        evidence: List[dict],
        confidence: float,
        reliability_score: float = 1.0,
    ) -> None:
        state.proposals.append(
            DebateProposal(
                agent_id=agent_id,
                proposal=proposal,
                evidence=evidence,
                confidence=confidence,
                reliability_score=reliability_score,
                round=state.round,
            )
        )
        state.history.append({
            "phase": DebatePhase.PROPOSE,
            "round": state.round,
            "agent": agent_id,
            "confidence": confidence,
        })

    def add_critique(
        self,
        state: DebateState,
        critic_id: str,
        target_id: str,
        issues: List[str],
        suggestions: List[str],
        confidence: float,
    ) -> None:
        state.critiques.append(
            DebateCritique(
                critic_agent_id=critic_id,
                target_agent_id=target_id,
                issues=issues,
                suggested_fixes=suggestions,
                confidence=confidence,
                round=state.round,
            )
        )
        state.history.append({
            "phase": DebatePhase.CRITIQUE,
            "round": state.round,
            "critic": critic_id,
            "target": target_id,
            "issue_count": len(issues),
        })

    def aggregate(self, state: DebateState) -> DebateState:
        """Compute weighted consensus from all proposals and critiques."""
        if not state.proposals:
            state.requires_human_review = True
            state.phase = DebatePhase.DONE
            return state

        # Build aggregation context
        proposals_text = json.dumps(
            [
                {
                    "agent": p.agent_id,
                    "proposal": p.proposal,
                    "evidence": p.evidence,
                    "confidence": p.confidence,
                    "reliability": p.reliability_score,
                    "weighted_score": p.confidence * p.reliability_score,
                }
                for p in state.proposals
            ],
            indent=2,
        )
        critiques_text = json.dumps(
            [
                {
                    "critic": c.critic_agent_id,
                    "target": c.target_agent_id,
                    "issues": c.issues,
                    "fixes": c.suggested_fixes,
                }
                for c in state.critiques
            ],
            indent=2,
        )

        prompt = f"""Proposals (round {state.round}):
{proposals_text}

Critiques:
{critiques_text}

Synthesize the best final output."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            system=AGGREGATOR_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)
        final_confidence = result.get("confidence", 0.0)

        state.history.append({
            "phase": DebatePhase.AGGREGATE,
            "round": state.round,
            "confidence": final_confidence,
        })

        if final_confidence >= self.confidence_threshold:
            # Accept — debate done
            state.final_result = result
            state.phase = DebatePhase.DONE
            logger.info(
                f"Debate resolved for task {state.task_id} "
                f"(confidence={final_confidence:.2f}, round={state.round})"
            )
        elif state.round >= state.max_rounds:
            # Max rounds reached — escalate if still below threshold
            state.final_result = result
            state.requires_human_review = final_confidence < self.escalation_threshold
            state.phase = DebatePhase.DONE
            logger.warning(
                f"Debate max rounds reached for task {state.task_id}. "
                f"Human review: {state.requires_human_review}"
            )
        else:
            # More rounds needed
            state.round += 1
            state.phase = DebatePhase.PROPOSE
            logger.info(
                f"Debate continuing for task {state.task_id} "
                f"(round {state.round}, confidence={final_confidence:.2f})"
            )

        return state

    def get_summary(self, state: DebateState) -> dict:
        return {
            "task_id": state.task_id,
            "rounds_completed": state.round,
            "proposals_count": len(state.proposals),
            "critiques_count": len(state.critiques),
            "final_confidence": state.final_result.get("confidence", 0) if state.final_result else 0,
            "requires_human_review": state.requires_human_review,
            "history": state.history,
        }
