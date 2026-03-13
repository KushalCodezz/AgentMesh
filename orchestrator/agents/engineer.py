"""
agents/engineer.py — EngineerAgent.
Implements code, tests, Dockerfiles, and CI/CD configs.
Runs a lightweight syntax validation step before returning.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import tempfile
from typing import Any, Dict, List

import anthropic

from agents.base import BaseAgent
from core.envelope import AgentResult, CapabilityTag, ProvenanceRef, TaskSpec

SYSTEM_PROMPT = """You are a senior software engineer. You write clean, production-ready code 
with tests, type hints, docstrings, and error handling. You follow best practices.

Rules:
1. Always write tests (pytest for Python, jest for JS/TS)
2. Include a Dockerfile where appropriate
3. Add meaningful comments and docstrings
4. Handle errors gracefully
5. Provide a README with setup instructions

Return ONLY valid JSON:
{
  "summary": "What was built and why",
  "files": [
    {
      "filename": "main.py",
      "language": "python",
      "content": "# full file content here",
      "description": "Entry point for the service"
    }
  ],
  "test_results": {
    "tests_written": 5,
    "test_commands": ["pytest tests/ -v"],
    "expected_pass_rate": 1.0
  },
  "setup_instructions": ["pip install -r requirements.txt", "python main.py"],
  "dependencies": ["fastapi", "pydantic"],
  "architecture_notes": "...",
  "confidence": 0.9
}"""


def _validate_python(code: str) -> tuple[bool, str]:
    """Quick AST parse to catch syntax errors."""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, str(e)


class EngineerAgent(BaseAgent):
    agent_id = "engineer_agent"
    capabilities = [CapabilityTag.CODE]
    model_preference = "claude"

    def __init__(self):
        super().__init__()
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    async def _execute(self, task: TaskSpec) -> AgentResult:
        context_parts = [
            f"Task: {task.title}",
            f"Description: {task.description}",
        ]

        response = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=6000,
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

        # Run syntax validation on Python files
        syntax_issues = []
        for file_info in output.get("files", []):
            if file_info.get("language") == "python":
                valid, error = _validate_python(file_info.get("content", ""))
                if not valid:
                    syntax_issues.append(f"{file_info['filename']}: {error}")

        if syntax_issues:
            output["syntax_warnings"] = syntax_issues

        confidence = float(output.get("confidence", 0.9))
        if syntax_issues:
            confidence = max(0.5, confidence - 0.2)

        # Build refs for each file
        refs = []
        for i, file_info in enumerate(output.get("files", [])):
            refs.append(
                self.make_ref(
                    ref_type="object",
                    ref_id=f"code_{task.task_id}_{i}",
                    description=file_info.get("description", file_info.get("filename")),
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
