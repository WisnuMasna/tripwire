"""Claude triage — turn an enriched session into a structured assessment (Phase 3).

Uses the Anthropic SDK's structured-output path (`messages.parse` with a Pydantic
schema), so the result is guaranteed to validate — no brittle JSON parsing.
Model + prompt are both externally configurable (env / prompts file).
"""
from __future__ import annotations

import json
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

from config import settings


class TriageResult(BaseModel):
    summary: str
    mitre_techniques: list[str] = Field(default_factory=list)
    notability_score: int          # 1-5
    notability_reason: str


_PROMPT = (Path(__file__).parent / "prompts" / "triage_prompt.md").read_text(encoding="utf-8")
_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def triage_session(session: dict) -> TriageResult:
    resp = await _client.messages.parse(
        model=settings.anthropic_model,
        max_tokens=1024,
        # Triage is a light classification task at high volume — keep thinking off
        # to control cost/latency. Switch to {"type": "adaptive"} for richer scoring.
        thinking={"type": "disabled"},
        system=_PROMPT,
        messages=[{"role": "user", "content": json.dumps(session, default=str)}],
        output_format=TriageResult,
    )
    return resp.parsed_output
