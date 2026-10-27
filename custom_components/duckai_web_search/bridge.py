"""Small HTTP client for the Duck.ai bridge."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession


class DuckBridgeError(HomeAssistantError):
    """Bridge request failed."""


async def async_get_models(hass: HomeAssistant, url: str) -> list[dict[str, Any]]:
    """Return the model list published by the bridge."""
    try:
        session = async_get_clientsession(hass)
        async with session.get(
            f"{url.rstrip('/')}/models", timeout=aiohttp.ClientTimeout(total=25)
        ) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        raise DuckBridgeError(f"Cannot load models: {exc}") from exc
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise DuckBridgeError("Invalid models response")
    return [
        m for m in models
        if isinstance(m, dict) and isinstance(m.get("id"), str) and m["id"]
    ]


async def async_post(
    hass: HomeAssistant, url: str, path: str, body: dict[str, Any]
) -> dict[str, Any]:
    """POST JSON to the bridge and return the decoded payload."""
    try:
        session = async_get_clientsession(hass)
        async with session.post(
            f"{url.rstrip('/')}{path}",
            json=body,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as response:
            payload = await response.json(content_type=None)
            if response.status != 200:
                error = payload.get("error", "unknown error") if isinstance(payload, dict) else "unknown error"
                raise DuckBridgeError(f"Duck.ai bridge HTTP {response.status}: {error}")
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        raise DuckBridgeError(f"Duck.ai bridge connection failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise DuckBridgeError("Invalid bridge response")
    return payload
