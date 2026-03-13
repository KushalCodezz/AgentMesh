"""
core/orchestrator.py — Central Orchestration Engine.
Coordinates the full task lifecycle:
  Plan → Dispatch → Debate → Validate → Adapt → Deliver
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.adaptive import AdaptiveLayer, TaskOutcome
from core.debate import DebateEngine
from core.envelope import (
    AgentResult,
    CapabilityTag,
    TaskSpec,
    TaskStatus,
)
from core.planner import TaskPlanner

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Central brain of the AI Office.
    
    Lifecycle per user request:
    1.  Plan     — TaskPlanner converts request → TaskSpec DAG
    2.  Dispatch — Route each TaskSpec to capable agent(s)
    3.  Debate   — High-impact tasks go through DebateEngine
    4.  Validate — QAAgent cross-checks every primary output
    5.  Adapt    — AdaptiveLayer analyzes gaps, proposes agents
    6.  Deliver  — Package all results + refs into final deliverable
    """

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.planner = TaskPlanner(api_key)
        self.debate_engine = DebateEngine(
            api_key,
            confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.75")),
            escalation_threshold=float(os.getenv("ESCALATION_THRESHOLD", "0.60")),
            max_rounds=int(os.getenv("MAX_DEBATE_ROUNDS", "3")),
        )
        self.adaptive = AdaptiveLayer(
            api_key,
            window_size=int(os.getenv("ADAPTIVE_WINDOW_SIZE", "200")),
            failure_threshold=int(os.getenv("ADAPTIVE_FAILURE_THRESHOLD", "8")),
            confidence_threshold=float(os.getenv("ADAPTIVE_CONFIDENCE_THRESHOLD", "0.6")),
            auto_register=os.getenv("ADAPTIVE_AUTO_REGISTER", "false").lower() == "true",
        )

        # Agent registry — lazy import to avoid circular deps
        self._agents: Dict[str, Any] = {}
        self._capability_map: Dict[CapabilityTag, List[str]] = {}
        self._conversations: Dict[str, dict] = {}
        self._tasks: Dict[str, TaskSpec] = {}
        self._results: Dict[str, AgentResult] = {}

        self._register_default_agents()

    def _register_default_agents(self) -> None:
        from agents.architect import ArchitectAgent
        from agents.creative import CreativeAgent
        from agents.engineer import EngineerAgent
        from agents.product_manager import ProductManagerAgent
        from agents.qa import QAAgent

        defaults = [
            ProductManagerAgent(),
            ArchitectAgent(),
            EngineerAgent(),
            QAAgent(),
            CreativeAgent(),
        ]
        for agent in defaults:
            self._agents[agent.agent_id] = agent
            for cap in agent.capabilities:
                self._capability_map.setdefault(cap, []).append(agent.agent_id)

        logger.info(f"Registered {len(self._agents)} agents")

    # ── Public API ─────────────────────────────────────────────────────────

    async def start_conversation(
        self, user_request: str, metadata: Optional[dict] = None
    ) -> dict:
        """Entry point: create a conversation and kick off planning."""
        conversation_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())

        conv = {
            "conversation_id": conversation_id,
            "trace_id": trace_id,
            "request": user_request,
            "status": "planning",
            "tasks": [],
            "results": {},
            "deliverable": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "events": [],
        }
        self._conversations[conversation_id] = conv
        self._emit_event(conv, "conversation_started", {"request": user_request[:200]})

        # Kick off async execution
        asyncio.create_task(self._run_conversation(conversation_id, user_request, trace_id))

        return {
            "conversation_id": conversation_id,
            "trace_id": trace_id,
            "status": "planning",
        }

    async def get_conversation(self, conversation_id: str) -> Optional[dict]:
        return self._conversations.get(conversation_id)

    async def list_conversations(self) -> List[dict]:
        return [
            {
                "conversation_id": c["conversation_id"],
                "status": c["status"],
                "request": c["request"][:120],
                "task_count": len(c["tasks"]),
                "created_at": c["created_at"],
            }
            for c in self._conversations.values()
        ]

    def get_agent_stats(self) -> List[dict]:
        return [a.get_stats() for a in self._agents.values()]

    def get_adaptive_proposals(self) -> List[dict]:
        return self.adaptive.get_proposals()

    async def approve_agent_proposal(self, proposal_id: str) -> bool:
        return self.adaptive.approve_proposal(proposal_id)

    async def reject_agent_proposal(self, proposal_id: str) -> bool:
        return self.adaptive.reject_proposal(proposal_id)

    # ── Internal pipeline ─────────────────────────────────────────────────

    async def _run_conversation(
        self, conversation_id: str, user_request: str, trace_id: str
    ) -> None:
        conv = self._conversations[conversation_id]
        try:
            # 1. Plan
            tasks = await self.planner.plan(user_request, conversation_id, trace_id)
            conv["tasks"] = [t.model_dump() for t in tasks]
            conv["status"] = "running"
            self._emit_event(conv, "planned", {"task_count": len(tasks)})

            for t in tasks:
                self._tasks[t.task_id] = t

            # 2. Execute DAG
            await self._execute_dag(conv, tasks)

            # 3. Adaptive analysis
            new_proposals = self.adaptive.run_full_cycle()
            if new_proposals:
                self._emit_event(
                    conv, "adaptive_proposals",
                    {"count": len(new_proposals), "proposals": [p.proposal_id for p in new_proposals]}
                )

            # 4. Package deliverable
            conv["deliverable"] = self._package_deliverable(conv, tasks)
            conv["status"] = "completed"
            self._emit_event(conv, "completed", {"deliverable": conv["deliverable"].get("summary", "")})

        except Exception as e:
            logger.error(f"Conversation {conversation_id} failed: {e}", exc_info=True)
            conv["status"] = "failed"
            conv["error"] = str(e)
            self._emit_event(conv, "failed", {"error": str(e)})

    async def _execute_dag(self, conv: dict, tasks: List[TaskSpec]) -> None:
        """Execute tasks in dependency order, parallelizing where possible."""
        pending = {t.task_id: t for t in tasks}
        completed_ids: set = set()

        while pending:
            # Find all tasks whose dependencies are satisfied
            ready = [
                t for t in pending.values()
                if all(dep in completed_ids for dep in t.depends_on)
            ]

            if not ready:
                # Cycle detection — break deadlock
                logger.warning("No ready tasks but pending tasks exist — possible cycle")
                break

            # Execute ready tasks in parallel
            results = await asyncio.gather(
                *[self._execute_task(conv, t) for t in ready],
                return_exceptions=True,
            )

            for task, result in zip(ready, results):
                if isinstance(result, Exception):
                    task.status = TaskStatus.FAILED
                    task.error = str(result)
                else:
                    completed_ids.add(task.task_id)

                del pending[task.task_id]
                # Sync back
                for i, t in enumerate(tasks):
                    if t.task_id == task.task_id:
                        tasks[i] = task
                        break

            # Update conv tasks snapshot
            conv["tasks"] = [t.model_dump() for t in tasks]

    async def _execute_task(self, conv: dict, task: TaskSpec) -> AgentResult:
        """Dispatch a single task: find agent → execute → (debate if needed) → record."""
        task.status = TaskStatus.RUNNING
        self._emit_event(conv, "task_started", {"task_id": task.task_id, "title": task.title})

        # Find best agent for capability
        agent = self._route(task.capability)
        if not agent:
            raise RuntimeError(f"No agent available for capability: {task.capability}")

        # Attach prior task refs as input
        task.input_refs = self._collect_refs_for(task, conv)

        result = await agent.execute(task)

        # Record outcome for adaptive layer
        self.adaptive.record_outcome(TaskOutcome(
            task_id=task.task_id,
            capability=task.capability.value,
            agent_id=agent.agent_id,
            success=result.success,
            confidence=result.confidence,
            latency_ms=result.latency_ms,
            error_signature=result.error[:60] if result.error else None,
        ))

        # Debate high-impact tasks
        requires_debate = task.meta_requires_debate if hasattr(task, "meta_requires_debate") else False
        if requires_debate and result.success:
            result = await self._run_debate(conv, task, result, agent)

        task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
        task.result = result.output
        task.confidence = result.confidence

        if result.requires_human_review:
            task.status = TaskStatus.AWAITING_HUMAN
            self._emit_event(conv, "human_review_required", {"task_id": task.task_id})

        conv["results"][task.task_id] = result.model_dump()
        self._results[task.task_id] = result

        self._emit_event(conv, "task_completed", {
            "task_id": task.task_id,
            "success": result.success,
            "confidence": result.confidence,
        })

        return result

    async def _run_debate(
        self, conv: dict, task: TaskSpec, primary_result: AgentResult, primary_agent: Any
    ) -> AgentResult:
        """Run multi-round debate for a high-impact task."""
        task.status = TaskStatus.DEBATE
        state = self.debate_engine.init_debate(task.task_id)

        self.debate_engine.add_proposal(
            state,
            agent_id=primary_agent.agent_id,
            proposal=primary_result.output,
            evidence=[e.model_dump() for e in primary_result.evidence],
            confidence=primary_result.confidence,
            reliability_score=primary_agent.reliability_score,
        )

        # Get a second opinion from QA agent
        qa_agent = self._agents.get("qa_agent")
        if qa_agent:
            qa_result = await qa_agent.execute(task)
            issues = qa_result.output.get("checks", [])
            self.debate_engine.add_critique(
                state,
                critic_id="qa_agent",
                target_id=primary_agent.agent_id,
                issues=[c.get("description", "") for c in issues if c.get("result") == "fail"],
                suggestions=qa_result.output.get("recommendations", []),
                confidence=qa_result.confidence,
            )

        state = self.debate_engine.aggregate(state)

        self._emit_event(conv, "debate_completed", self.debate_engine.get_summary(state))

        if state.final_result:
            return AgentResult(
                task_id=task.task_id,
                agent_id=primary_agent.agent_id,
                success=True,
                output=state.final_result.get("final_output", primary_result.output),
                confidence=state.final_result.get("confidence", primary_result.confidence),
                requires_human_review=state.requires_human_review,
            )
        return primary_result

    def _route(self, capability: CapabilityTag) -> Optional[Any]:
        """Return the best available agent for a capability."""
        agent_ids = self._capability_map.get(capability, [])
        if not agent_ids:
            return None
        # Pick highest reliability
        candidates = [(self._agents[aid], self._agents[aid].reliability_score) for aid in agent_ids]
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _collect_refs_for(self, task: TaskSpec, conv: dict) -> list:
        """Collect output refs from completed dependencies."""
        refs = []
        for dep_id in task.depends_on:
            result = self._results.get(dep_id)
            if result:
                refs.extend(result.refs)
        return refs

    def _package_deliverable(self, conv: dict, tasks: List[TaskSpec]) -> dict:
        """Assemble the final deliverable package."""
        all_results = [self._results.get(t.task_id) for t in tasks if self._results.get(t.task_id)]
        all_refs = []
        for r in all_results:
            if r:
                all_refs.extend([ref.model_dump() for ref in r.refs])

        human_review_tasks = [t.task_id for t in tasks if t.status == TaskStatus.AWAITING_HUMAN]
        avg_confidence = (
            sum(r.confidence for r in all_results if r) / len(all_results)
            if all_results else 0
        )

        return {
            "summary": f"Completed {len(tasks)} tasks with avg confidence {avg_confidence:.2f}",
            "task_results": {t.task_id: t.result for t in tasks if t.result},
            "all_refs": all_refs,
            "requires_human_review": human_review_tasks,
            "avg_confidence": round(avg_confidence, 3),
            "task_count": len(tasks),
            "success_count": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "assembled_at": datetime.now(timezone.utc).isoformat(),
        }

    def _emit_event(self, conv: dict, event_type: str, data: dict) -> None:
        conv["events"].append({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
