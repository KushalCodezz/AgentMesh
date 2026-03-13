"""
agents/creative.py — CreativeAgent.
Produces creative briefs, storyboards, copy, and media prompts.
(Full multimodal generation deferred to Gemini adapter.)
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

import anthropic

from agents.base import BaseAgent
from core.envelope import AgentResult, CapabilityTag, TaskSpec

SYSTEM_PROMPT = """You are a world-class creative director with expertise in branding, 
visual design, copywriting, and multimedia storytelling.

For every creative task:
1. Define clear creative direction and aesthetic vision
2. Produce detailed image prompts (for Stable Diffusion / DALL-E / Midjourney)
3. Write audio/video storyboard scripts
4. Generate marketing copy (headlines, body, CTAs)
5. Include rights/licensing notes

Return ONLY valid JSON:
{
  "creative_brief": {
    "concept": "...",
    "tone": "...",
    "target_audience": "...",
    "key_message": "..."
  },
  "image_prompts": [
    {
      "id": "img_1",
      "description": "...",
      "prompt": "Detailed Stable Diffusion prompt here",
      "negative_prompt": "...",
      "style": "photorealistic|illustration|3d_render|...",
      "aspect_ratio": "16:9|1:1|9:16"
    }
  ],
  "video_storyboard": [
    {
      "scene": 1,
      "duration_sec": 5,
      "visual": "...",
      "voiceover": "...",
      "music": "upbeat electronic | ambient | ..."
    }
  ],
  "copy": {
    "headline": "...",
    "subheadline": "...",
    "body": "...",
    "cta": "...",
    "social_captions": {"twitter": "...", "instagram": "...", "linkedin": "..."}
  },
  "rights_notes": "All prompts generate original content. No copyrighted IP referenced.",
  "confidence": 0.85
}"""


class CreativeAgent(BaseAgent):
    agent_id = "creative_agent"
    capabilities = [CapabilityTag.CREATIVE]
    model_preference = "gemini"

    def __init__(self):
        super().__init__()
        # Use Claude as fallback if Gemini not configured
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    async def _execute(self, task: TaskSpec) -> AgentResult:
        response = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=3000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Creative task: {task.title}\n\n"
                        f"Brief: {task.description}\n\n"
                        "Produce a complete creative package."
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
        confidence = float(output.get("confidence", 0.85))

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            output=output,
            confidence=confidence,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
        )
