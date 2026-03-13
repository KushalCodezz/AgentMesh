"""
core/adaptive.py — Adaptive Agent Creator.
Monitors task outcomes, detects recurring capability gaps, and proposes
(or auto-registers) new specialized agents to fill those gaps.
"""
from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import anthropic

logger = logging.getLogger(__name__)

AGENT_CREATOR_PROMPT = """You are an AI systems architect. Analyze the provided failure data 
and design a new specialized AI agent to address the recurring capability gap.

Return ONLY valid JSON:
{
  "agent_id": "snake_case_agent_name",
  "name": "Human Readable Name",
  "description": "What this agent does and why it was created",
  "capabilities": ["list", "of", "capabilities"],
  "required_tools": ["web_search", "code_executor", "file_reader"],
  "model_preference": "claude|deepseek|gemini",
  "system_prompt": "Full system prompt for this agent",
  "prompt_templates": [
    {
      "name": "template_name",
      "template": "Template with {placeholders}"
    }
  ],
  "test_cases": [
    {
      "input": "Sample input",
      "expected_output_contains": ["key phrase", "expected element"]
    }
  ],
  "safety_rules": ["list of safety constraints"],
  "is_high_impact": false,
  "requires_human_approval": false
}"""


@dataclass
class TaskOutcome:
    task_id: str
    capability: str
    agent_id: str
    success: bool
    confidence: float
    latency_ms: int
    error_signature: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentProposal:
    proposal_id: str
    spec: dict
    triggered_by: str  # capability that triggered this proposal
    failure_count: int
    avg_confidence: float
    status: str = "pending"  # pending | approved | rejected | deployed
    sandbox_passed: bool = False
    requires_human_approval: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AdaptiveLayer:
    """
    Monitors rolling window of task outcomes and proposes new agents
    when capability gaps exceed configured thresholds.
    
    Decision rules:
    - If capability X caused > FAILURE_THRESHOLD failures in window W
      AND avg_confidence < CONFIDENCE_THRESHOLD → propose new agent
    - Auto-register if is_high_impact=False AND ADAPTIVE_AUTO_REGISTER=True
    - Otherwise require human ops approval
    """

    def __init__(
        self,
        anthropic_api_key: str,
        window_size: int = 200,
        failure_threshold: int = 8,
        confidence_threshold: float = 0.6,
        auto_register: bool = False,
    ):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.window_size = window_size
        self.failure_threshold = failure_threshold
        self.confidence_threshold = confidence_threshold
        self.auto_register = auto_register

        self._outcomes: List[TaskOutcome] = []
        self._proposals: List[AgentProposal] = []
        self._registered_agents: Dict[str, dict] = {}

    def record_outcome(self, outcome: TaskOutcome) -> None:
        """Record a task outcome and trim window."""
        self._outcomes.append(outcome)
        if len(self._outcomes) > self.window_size:
            self._outcomes = self._outcomes[-self.window_size:]

    def analyze_gaps(self) -> List[dict]:
        """
        Analyze the rolling window and return capability gaps 
        that exceed the configured thresholds.
        """
        if not self._outcomes:
            return []

        # Group by capability
        by_cap: Dict[str, List[TaskOutcome]] = defaultdict(list)
        for o in self._outcomes:
            by_cap[o.capability].append(o)

        gaps = []
        for capability, outcomes in by_cap.items():
            failures = [o for o in outcomes if not o.success]
            if len(failures) < self.failure_threshold:
                continue

            avg_conf = sum(o.confidence for o in outcomes) / len(outcomes)
            if avg_conf >= self.confidence_threshold:
                continue

            # Check for repeated error signature
            error_sigs = Counter(
                o.error_signature for o in failures if o.error_signature
            )
            top_error = error_sigs.most_common(1)[0] if error_sigs else ("unknown", 0)

            gaps.append({
                "capability": capability,
                "failure_count": len(failures),
                "total_tasks": len(outcomes),
                "avg_confidence": round(avg_conf, 3),
                "failure_rate": round(len(failures) / len(outcomes), 3),
                "top_error_signature": top_error[0],
                "top_error_count": top_error[1],
                "avg_latency_ms": int(sum(o.latency_ms for o in outcomes) / len(outcomes)),
            })

        return gaps

    def propose_agent(self, gap: dict) -> Optional[AgentProposal]:
        """Use Claude to design a new specialized agent spec for the gap."""
        logger.info(f"Proposing new agent for capability gap: {gap['capability']}")

        context = json.dumps(gap, indent=2)
        response = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=3000,
            system=AGENT_CREATOR_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Design a specialized agent for this capability gap:\n\n{context}",
                }
            ],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        spec = json.loads(raw)

        import uuid
        proposal = AgentProposal(
            proposal_id=str(uuid.uuid4()),
            spec=spec,
            triggered_by=gap["capability"],
            failure_count=gap["failure_count"],
            avg_confidence=gap["avg_confidence"],
            requires_human_approval=spec.get("requires_human_approval", True),
        )
        self._proposals.append(proposal)
        return proposal

    def run_sandbox_test(self, proposal: AgentProposal) -> bool:
        """
        Run the proposed agent spec against its own test cases.
        Returns True if the agent passes all test cases.
        """
        spec = proposal.spec
        test_cases = spec.get("test_cases", [])
        if not test_cases:
            logger.warning(f"No test cases for proposal {proposal.proposal_id}")
            proposal.sandbox_passed = False
            return False

        passed = 0
        for tc in test_cases:
            try:
                response = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1000,
                    system=spec.get("system_prompt", "You are a helpful assistant."),
                    messages=[{"role": "user", "content": tc["input"]}],
                )
                output = response.content[0].text.lower()
                expected = [e.lower() for e in tc.get("expected_output_contains", [])]
                if all(e in output for e in expected):
                    passed += 1
            except Exception as e:
                logger.error(f"Sandbox test error: {e}")

        pass_rate = passed / len(test_cases) if test_cases else 0
        proposal.sandbox_passed = pass_rate >= 0.8
        logger.info(
            f"Sandbox test for {proposal.proposal_id}: "
            f"{passed}/{len(test_cases)} passed ({pass_rate:.1%})"
        )
        return proposal.sandbox_passed

    def register_agent(self, proposal: AgentProposal) -> bool:
        """Register an approved agent in the agent registry."""
        if not proposal.sandbox_passed:
            logger.warning(f"Cannot register agent — sandbox not passed: {proposal.proposal_id}")
            return False

        agent_id = proposal.spec["agent_id"]
        self._registered_agents[agent_id] = {
            **proposal.spec,
            "proposal_id": proposal.proposal_id,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        proposal.status = "deployed"
        logger.info(f"Registered new agent: {agent_id}")
        return True

    def run_full_cycle(self) -> List[AgentProposal]:
        """Full adaptive cycle: analyze → propose → sandbox → (register if auto)."""
        gaps = self.analyze_gaps()
        new_proposals = []

        for gap in gaps:
            # Skip if we already have a proposal for this capability
            existing = [
                p for p in self._proposals
                if p.triggered_by == gap["capability"]
                and p.status in ("pending", "deployed")
            ]
            if existing:
                continue

            proposal = self.propose_agent(gap)
            if not proposal:
                continue

            self.run_sandbox_test(proposal)

            if proposal.sandbox_passed and self.auto_register and not proposal.requires_human_approval:
                self.register_agent(proposal)

            new_proposals.append(proposal)

        return new_proposals

    def get_proposals(self) -> List[dict]:
        return [
            {
                "proposal_id": p.proposal_id,
                "triggered_by": p.triggered_by,
                "agent_name": p.spec.get("name"),
                "failure_count": p.failure_count,
                "avg_confidence": p.avg_confidence,
                "sandbox_passed": p.sandbox_passed,
                "status": p.status,
                "requires_human_approval": p.requires_human_approval,
                "created_at": p.created_at.isoformat(),
            }
            for p in self._proposals
        ]

    def approve_proposal(self, proposal_id: str) -> bool:
        for p in self._proposals:
            if p.proposal_id == proposal_id:
                p.status = "approved"
                return self.register_agent(p)
        return False

    def reject_proposal(self, proposal_id: str) -> bool:
        for p in self._proposals:
            if p.proposal_id == proposal_id:
                p.status = "rejected"
                return True
        return False
