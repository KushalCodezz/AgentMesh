"""
core/planner.py — Task DAG Planner.
Converts user intent into a directed acyclic graph of TaskSpec objects
with capability tags, priorities, and dependency chains.
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

import anthropic

from core.envelope import CapabilityTag, Priority, TaskSpec

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are a senior project manager AI. Your job is to decompose a user's 
request into a structured task DAG (directed acyclic graph) for an AI agent team.

Available agent capabilities:
- research: Deep web research, market analysis, fact-finding (uses DeepSeek)
- architecture: System design, API contracts, data modeling (uses Claude)
- code: Implementation, tests, Dockerfile (uses Claude)
- qa: Testing, validation, claim verification (uses Claude)
- creative: Images, audio, video, marketing copy (uses Gemini)
- planning: Project planning, scheduling, milestones (uses Claude)
- adaptive: Self-improvement, new agent proposals (internal)

Rules:
1. Decompose the request into 3-8 atomic tasks
2. Mark dependencies (a task can only start after its dependencies complete)
3. Assign the correct capability to each task
4. High-impact tasks (public content, external integrations) require requires_debate=true
5. Return ONLY valid JSON — no markdown, no extra text

Response schema:
{
  "tasks": [
    {
      "task_id": "t1",
      "capability": "research",
      "title": "Market Research",
      "description": "Detailed description of what to research",
      "depends_on": [],
      "priority": 80,
      "budget_tokens": 3000,
      "requires_debate": false
    }
  ]
}"""


class TaskPlanner:
    """Converts user intent to a TaskSpec DAG using Claude as the planner."""

    def __init__(self, anthropic_api_key: str):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)

    async def plan(
        self,
        user_request: str,
        conversation_id: str,
        trace_id: str,
    ) -> List[TaskSpec]:
        """Generate a task DAG from a natural language user request."""
        logger.info(f"Planning tasks for conversation {conversation_id}")

        response = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            system=PLANNER_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Decompose this request into tasks:\n\n{user_request}",
                }
            ],
        )

        raw = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)
        tasks = []

        for t in data.get("tasks", []):
            task = TaskSpec(
                task_id=t.get("task_id", f"t_{len(tasks)+1}"),
                conversation_id=conversation_id,
                trace_id=trace_id,
                capability=CapabilityTag(t.get("capability", "research")),
                title=t.get("title", "Untitled Task"),
                description=t.get("description", ""),
                depends_on=t.get("depends_on", []),
                priority=t.get("priority", Priority.NORMAL),
                budget_tokens=t.get("budget_tokens", 4000),
                meta_requires_debate=t.get("requires_debate", False),
            )
            tasks.append(task)

        logger.info(f"Planned {len(tasks)} tasks for {conversation_id}")
        return tasks

    def get_ready_tasks(self, all_tasks: List[TaskSpec]) -> List[TaskSpec]:
        """Return tasks whose dependencies have all completed."""
        completed_ids = {t.task_id for t in all_tasks if t.status.value == "completed"}
        ready = []
        for task in all_tasks:
            if task.status.value == "pending":
                if all(dep in completed_ids for dep in task.depends_on):
                    ready.append(task)
        return ready

    def is_dag_complete(self, all_tasks: List[TaskSpec]) -> bool:
        """Return True if every task in the DAG has completed or failed."""
        return all(t.status.value in ("completed", "failed") for t in all_tasks)
