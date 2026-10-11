"""Opt-in OpenAI Responses client with a cancellable wall-clock deadline.

API contract: https://developers.openai.com/api/docs/guides/structured-outputs
No retries here: the resolver reserves and charges each attempt explicitly.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal, ROUND_CEILING
import json
import os

from laughtrack.core.comedy_eligibility_model import ModelConfig, ProviderResult
from laughtrack.core.comedy_eligibility_store import canonical_json

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decision": {"type": "string", "enum": ["accept", "reject", "review"]},
        "evidence_kind": {"type": "string", "enum": ["comedy", "non_comedy", "uncertain"]},
        "citations": {
            "type": "array",
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "field": {"type": "string", "enum": ["name", "description"]},
                    "quote": {"type": "string"},
                },
                "required": ["field", "quote"],
            },
        },
    },
    "required": ["decision", "evidence_kind", "citations"],
}


class OpenAIComedyProvider:
    def __init__(self, *, api_key=None, input_usd_per_million=None, output_usd_per_million=None, transport=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.input_rate = Decimal(str(input_usd_per_million or os.getenv("COMEDY_MODEL_INPUT_USD_PER_MILLION", "0")))
        self.output_rate = Decimal(str(output_usd_per_million or os.getenv("COMEDY_MODEL_OUTPUT_USD_PER_MILLION", "0")))
        self.transport = transport
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required only for optional enrichment")
        if any(not r.is_finite() or r <= 0 for r in (self.input_rate, self.output_rate)):
            raise ValueError("Configure verified per-million token prices for the selected model")

    def complete(self, *, system: str, context: dict, config: ModelConfig) -> ProviderResult:
        if not config.enabled or config.provider != "openai":
            raise ValueError("OpenAI enrichment must be explicitly enabled")
        if len(canonical_json(context)) > config.max_input_chars:
            raise ValueError("Input exceeds configured bound")
        # Only event fields are sent. Identity snapshots remain in the cache key
        # and deterministic protection rules, not in the model's genre evidence.
        event = {k: context["event"].get(k) or "" for k in ("name", "description")}
        body = {
            "model": config.model,
            "store": False,
            "max_output_tokens": config.max_output_tokens,
            "instructions": system,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": canonical_json(event)}]}],
            "text": {"format": {"type": "json_schema", "name": "comedy_eligibility", "strict": True, "schema": SCHEMA}},
        }
        # One token per UTF-8 byte plus framing margin deliberately overestimates
        # text tokenization. Operators must supply current model prices.
        upper_input_tokens = len(canonical_json(body).encode("utf-8")) + 1024
        upper_cost = self._cost(upper_input_tokens, config.max_output_tokens)
        if upper_cost > config.max_cost_micros:
            raise ValueError("Maximum possible request cost exceeds its reservation")
        return asyncio.run(self._deadline_request(body, config))

    def _cost(self, inputs, outputs):
        # USD / million tokens equals USD-micros / token.
        return int((inputs * self.input_rate + outputs * self.output_rate).to_integral_value(rounding=ROUND_CEILING))

    async def _deadline_request(self, body, config) -> ProviderResult:
        return await asyncio.wait_for(self._request(body, config), timeout=config.timeout_seconds)

    async def _request(self, body, config) -> ProviderResult:
        import httpx

        async with httpx.AsyncClient(
            timeout=config.timeout_seconds, transport=self.transport, follow_redirects=False, trust_env=False
        ) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
            ) as response:
                response.raise_for_status()
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 128000:
                        raise ValueError("Provider response exceeds size bound")
        result = json.loads(data)
        usage = result.get("usage") or {}
        inputs, outputs = usage.get("input_tokens"), usage.get("output_tokens")
        if any(type(v) is not int or v < 0 for v in (inputs, outputs)):
            raise ValueError("Missing provider token usage; retain full reservation")
        cost = self._cost(inputs, outputs)
        contents = [
            part
            for item in result.get("output", [])
            if item.get("type") == "message"
            for part in item.get("content", [])
        ]
        texts = [p.get("text") for p in contents if p.get("type") == "output_text"]
        parsed = None
        if (
            result.get("status") == "completed"
            and len(texts) == 1
            and not any(p.get("type") == "refusal" for p in contents)
        ):
            try:
                parsed = json.loads(texts[0])
            except (ValueError, TypeError):
                pass
        return ProviderResult(
            parsed,
            cost,
            {
                "input_tokens": inputs,
                "output_tokens": outputs,
                "response_id": result.get("id"),
                "status": result.get("status"),
            },
        )
