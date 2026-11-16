"""Thin wrapper around the Anthropic SDK for structured JSON calls."""
from __future__ import annotations

import logging
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from .config import ClaudeConfig

log = logging.getLogger("paperfeed.claude")

T = TypeVar("T", bound=BaseModel)

# Models that accept the server-side `fallbacks: "default"` parameter.
FALLBACK_MODELS = ("claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1", "claude-fable-5-2")
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class RefusalError(RuntimeError):
    pass


class Claude:
    def __init__(self, cfg: ClaudeConfig):
        self.cfg = cfg
        self.client = anthropic.Anthropic()

    def structured(self, *, system: list[dict], user: str, schema: type[T], effort: str, max_tokens: int = 32000) -> T:
        kwargs: dict = dict(
            model=self.cfg.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
            output_config={"effort": effort},
        )
        if self.cfg.fallbacks and self.cfg.model in FALLBACK_MODELS:
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        with self.client.beta.messages.stream(**kwargs) as stream:
            msg = stream.get_final_message()
        u = msg.usage
        log.info(
            "claude %s: in=%s cache_read=%s cache_write=%s out=%s stop=%s",
            msg.model, u.input_tokens, getattr(u, "cache_read_input_tokens", None),
            getattr(u, "cache_creation_input_tokens", None), u.output_tokens, msg.stop_reason,
        )
        if msg.stop_reason == "refusal":
            raise RefusalError(str(getattr(msg, "stop_details", "") or "refused"))
        if msg.stop_reason == "max_tokens":
            raise RuntimeError("output truncated (max_tokens)")
        text = "".join(b.text for b in msg.content if b.type == "text")
        return schema.model_validate_json(text)


def system_blocks(instructions: str, persona: str) -> list[dict]:
    """Stable prefix (instructions + persona) marked for prompt caching."""
    return [
        {"type": "text", "text": instructions},
        {
            "type": "text",
            "text": f"# 読者のペルソナ\n\n{persona}",
            "cache_control": {"type": "ephemeral"},
        },
    ]
