"""Duck.ai conversation agent backed by the local Node.js bridge."""
from __future__ import annotations

import asyncio
import logging
import uuid

import aiohttp
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import MATCH_ALL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import intent

from .const import CONF_MODEL, CONF_URL, CONF_PROMPT, DEFAULT_PROMPT

_LOGGER = logging.getLogger(__name__)
MAX_TURNS = 12


class DuckConversationAgent(conversation.AbstractConversationAgent):
    """Conversation agent that forwards user messages to Duck.ai."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._histories: dict[str, list[dict[str, str]]] = {}

    @property
    def supported_languages(self) -> str:
        return MATCH_ALL

    async def async_process(self, user_input: conversation.ConversationInput) -> conversation.ConversationResult:
        conversation_id = user_input.conversation_id or uuid.uuid4().hex
        history = self._histories.get(conversation_id, [])
        messages = [*history[-MAX_TURNS * 2:], {"role": "user", "content": user_input.text}]
        response = intent.IntentResponse(language=user_input.language)
        try:
            session = async_get_clientsession(self.hass)
            async with session.post(
                self.entry.data[CONF_URL].rstrip("/") + "/chat",
                json={
                    "model": self.entry.options.get(CONF_MODEL, self.entry.data[CONF_MODEL]),
                    "system_prompt": self.entry.options.get(CONF_PROMPT, DEFAULT_PROMPT),
                    "messages": messages,
                    "web_search": False,
                },
                timeout=aiohttp.ClientTimeout(total=120),
            ) as http_response:
                payload = await http_response.json()
                if http_response.status != 200:
                    raise RuntimeError(f"Bridge HTTP {http_response.status}: {payload.get('error', 'Unknown error')}")
            answer = payload.get("answer", "")
            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError("Duck.ai returned an empty answer")
            response.async_set_speech(answer)
            self._histories[conversation_id] = [*messages, {"role": "assistant", "content": answer}][-MAX_TURNS * 2:]
            if len(self._histories) > 100:
                self._histories.pop(next(iter(self._histories)))
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError, ValueError) as exc:
            _LOGGER.warning("Duck.ai conversation failed: %s", exc)
            response.async_set_error(intent.IntentResponseErrorCode.UNKNOWN, "Duck.ai недоступен. Проверьте Bridge и журналы Home Assistant.")
        return conversation.ConversationResult(response=response, conversation_id=conversation_id)
