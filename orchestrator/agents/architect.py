"""
agents/architect.py — ArchitectAgent.
Produces system architecture, API contracts, data models,
scalability analysis, and security posture reviews.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

import anthropic

from agents.base import BaseAgent
from core.envelope import AgentResult, CapabilityTag, TaskSpec

SYSTEM_PROMPT = """You are a principal systems architect with 20 years of experience designing 
production systems at scale. You think in systems, APIs, data flows, and failure modes.

For every architecture task:
1. Produce a clear textual system diagram (ASCII)
2. Define all API contracts (REST or GraphQL)
3. Design the complete data model
4. Estimate cost at scale (1K, 10K, 100K users)
5. List top 5 security risks and mitigations
6. Identify open risks and technical debt

Return ONLY valid JSON:
{
  "executive_summary": "...",
  "architecture": {
    "diagram": "ASCII diagram here",
    "components": [
      {
        "name": "...",
        "type": "service|database|queue|cache|cdn",
        "description": "...",
        "technology": "FastAPI|PostgreSQL|Redis|...",
        "scaling_strategy": "..."
      }
    ],
    "data_flows": ["User → API Gateway → Auth Service → ...", "..."]
  },
  "api_contracts": [
    {
      "endpoint": "POST /api/v1/conversations",
      "method": "POST",
      "request_schema": {"conversation_id": "string", "request": "string"},
      "response_schema": {"task_ids": ["string"], "status": "string"},
      "auth": "bearer_jwt",
      "rate_limit": "100/min"
    }
  ],
  "data_model": {
    "entities": [
      {
        "name": "Conversation",
        "fields": [{"name": "id", "type": "uuid", "description": "..."}],
        "indexes": ["id", "created_at"],
        "relationships": ["has_many Tasks"]
      }
    ]
  },
  "cost_estimate": {
    "1k_users_monthly_usd": 50,
    "10k_users_monthly_usd": 400,
    "100k_users_monthly_usd": 3500,
    "assumptions": [...]
  },
  "security": {
    "auth_strategy": "...",
    "risks": [
      {"risk": "...", "severity": "high|medium|low", "mitigation": "..."}
    ]
  },
  "open_risks": [...],
  "tech_stack": ["FastAPI", "PostgreSQL", "Redis", "ChromaDB", "S3"],
  "confidence": 0.9
}"""


class ArchitectAgent(BaseAgent):
    agent_id = "architect_agent"
    capabilities = [CapabilityTag.ARCHITECTURE]
    model_preference = "claude"

    def __init__(self):
        super().__init__()
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    async def _execute(self, task: TaskSpec) -> AgentResult:
        # Include input refs context if available
        context_parts = [
            f"Task: {task.title}",
            f"Description: {task.description}",
        ]
        if task.input_refs:
            context_parts.append(
                f"\nInput refs available: {[r.description for r in task.input_refs]}"
            )

        response = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": "\n\n".join(context_parts),
                }
            ],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        output: Dict[str, Any] = json.loads(raw)
        confidence = float(output.get("confidence", 0.85))

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            output=output,
            confidence=confidence,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
        )
