"""LLM provider abstraction with deterministic local fallback."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMStatus:
    provider: str
    model: str
    available: bool
    reason: str


class LLMClient:
    """Thin abstraction over OpenAI API with safe deterministic fallback."""

    def __init__(self, model: str | None = None, enabled: bool = True) -> None:
        self.model = model or os.environ.get("FEATUREFORGE_MODEL", "gpt-4o-mini")
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.enabled = enabled

    def status(self) -> LLMStatus:
        if not self.enabled:
            return LLMStatus(
                provider="deterministic-local",
                model="local-rule-engine",
                available=False,
                reason="LLM disabled by configuration; using deterministic local baseline.",
            )
        if not self.api_key:
            return LLMStatus(
                provider="deterministic-local",
                model="local-rule-engine",
                available=False,
                reason="OPENAI_API_KEY not set; using deterministic local baseline.",
            )
        return LLMStatus(
            provider="openai",
            model=self.model,
            available=True,
            reason="OPENAI_API_KEY detected in environment.",
        )

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback_payload: dict[str, Any],
        timeout_sec: float = 20.0,
    ) -> tuple[dict[str, Any], str]:
        """Attempt structured JSON completion; fall back cleanly on any error."""
        st = self.status()
        if not st.available:
            return fallback_payload, f"fallback:{st.reason}"

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key, timeout=timeout_sec)
            resp = client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = resp.choices[0].message.content or "{}"
            parsed = json.loads(content)
            if isinstance(parsed, dict) and parsed:
                return parsed, f"openai:{self.model}"
        except Exception as exc:
            return fallback_payload, f"fallback:llm_error:{type(exc).__name__}"

        return fallback_payload, "fallback:empty_response"
