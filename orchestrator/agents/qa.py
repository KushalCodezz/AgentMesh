"""
agents/qa.py — QAAgent.
Validates code quality, verifies research claims,
runs static analysis, and produces QA reports.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

import anthropic

from agents.base import BaseAgent
from core.envelope import AgentResult, CapabilityTag, TaskSpec

SYSTEM_PROMPT = """You are a senior QA engineer and fact-checker. Your job is to rigorously 
validate deliverables produced by other agents.

For code: review for bugs, security issues, test coverage, style
For research: verify claims are plausible, sources are cited, confidence is calibrated
For architecture: check for single points of failure, missing error handling, security gaps
For creative: verify rights metadata, quality thresholds

Return ONLY valid JSON:
{
  "overall_result": "pass|fail|conditional_pass",
  "overall_confidence": 0.85,
  "checks": [
    {
      "check_id": "C1",
      "check_type": "syntax|security|coverage|fact|rights|style",
      "description": "...",
      "result": "pass|fail|warning",
      "severity": "critical|high|medium|low",
      "details": "...",
      "line_ref": null
    }
  ],
  "summary": {
    "pass_count": 8,
    "fail_count": 1,
    "warning_count": 2,
    "critical_issues": []
  },
  "recommendations": ["...", "..."],
  "requires_human_review": false,
  "test_commands": ["pytest tests/ -v --cov"],
  "confidence": 0.9
}"""


class QAAgent(BaseAgent):
    agent_id = "qa_agent"
    capabilities = [CapabilityTag.QA]
    model_preference = "claude"

    def __init__(self):
        super().__init__()
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    async def _execute(self, task: TaskSpec) -> AgentResult:
        # Build context from task and any input refs
        context_parts = [
            f"Task to validate: {task.title}",
            f"Validation scope: {task.description}",
        ]

        response = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=3000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "\n\n".join(context_parts)}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        output: Dict[str, Any] = json.loads(raw)
        confidence = float(output.get("confidence", 0.85))
        requires_human = output.get("requires_human_review", False)

        # Auto-flag critical failures
        summary = output.get("summary", {})
        if summary.get("critical_issues"):
            requires_human = True
            confidence = min(confidence, 0.5)

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=output.get("overall_result") != "fail",
            output=output,
            confidence=confidence,
            requires_human_review=requires_human,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
        )
