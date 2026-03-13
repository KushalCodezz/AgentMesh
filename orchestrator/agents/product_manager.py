"""
agents/product_manager.py — ProductManagerAgent.
Handles market research, PRD generation, competitor analysis,
feature prioritization. Backed by DeepSeek/Claude.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

import anthropic

from agents.base import BaseAgent
from core.envelope import AgentResult, CapabilityTag, ProvenanceRef, TaskSpec

SYSTEM_PROMPT = """You are a world-class product manager and researcher. Your output must be 
comprehensive, evidence-backed, and production-ready.

For every task you must:
1. Conduct thorough market/domain research
2. Identify top competitors with URLs
3. Extract top 10 supporting sources with URL + key excerpt
4. List prioritized features with acceptance criteria
5. Assign confidence scores (0.0-1.0) to every factual claim

Return ONLY valid JSON with this schema:
{
  "executive_summary": "2-3 sentence summary",
  "problem_statement": "...",
  "target_users": [{"segment": "...", "pain_points": [...]}],
  "market_size": {"tam": "...", "sam": "...", "confidence": 0.8},
  "competitors": [
    {
      "name": "...",
      "url": "...",
      "strengths": [...],
      "weaknesses": [...],
      "pricing": "..."
    }
  ],
  "sources": [
    {"title": "...", "url": "...", "excerpt": "...", "confidence": 0.9}
  ],
  "feature_backlog": [
    {
      "id": "F1",
      "title": "...",
      "description": "...",
      "priority": "P1|P2|P3",
      "acceptance_criteria": [...],
      "effort_days": 5,
      "confidence": 0.9
    }
  ],
  "risks": [{"risk": "...", "mitigation": "...", "likelihood": "high|medium|low"}],
  "overall_confidence": 0.85
}"""


class ProductManagerAgent(BaseAgent):
    agent_id = "product_manager_agent"
    capabilities = [CapabilityTag.RESEARCH, CapabilityTag.PLANNING]
    model_preference = "claude"

    def __init__(self):
        super().__init__()
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    async def _execute(self, task: TaskSpec) -> AgentResult:
        response = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Task: {task.title}\n\n"
                        f"Description: {task.description}\n\n"
                        f"Produce a complete PRD and research report."
                    ),
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
        confidence = float(output.get("overall_confidence", 0.8))

        # Build provenance refs from sources
        refs = []
        for i, src in enumerate(output.get("sources", [])[:10]):
            refs.append(
                self.make_ref(
                    ref_type="url",
                    ref_id=f"src_{task.task_id}_{i}",
                    description=src.get("title", ""),
                    source_url=src.get("url", ""),
                )
            )

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            output=output,
            refs=refs,
            confidence=confidence,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
        )
