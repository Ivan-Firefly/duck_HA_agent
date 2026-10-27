"""Duck.ai conversation agent entity (forwarded platform)."""
from __future__ import annotations

import logging

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import intent
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import async_post
from .const import (
    CONF_MODEL,
    CONF_PROMPT,
    CONF_URL,
    CONF_WEB_SEARCH,
    DEFAULT_PROMPT,
    DOMAIN,
    MAX_TURNS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([DuckConversationEntity(config_entry)])


class DuckConversationEntity(conversation.ConversationEntity):
    """Conversation agent that forwards the dialog to Duck.ai via the bridge."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supports_streaming = False

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="DuckDuckGo",
            model="Duck.ai",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def supported_languages(self) -> str:
        return MATCH_ALL

    async def _async_handle_message(
        self, user_input: conversation.ConversationInput, chat_log: conversation.ChatLog
    ) -> conversation.ConversationResult:
        # chat_log already contains the current user message and prior turns
        # (history is managed by Home Assistant per conversation_id).
        messages = [
            {"role": c.role, "content": c.content}
            for c in chat_log.content
            if c.role in ("user", "assistant") and c.content
        ][-(MAX_TURNS * 2 + 1):]

        data, options = self.entry.data, self.entry.options
        response = intent.IntentResponse(language=user_input.language)
        try:
            payload = await async_post(
                self.hass,
                data[CONF_URL],
                "/chat",
                {
                    "model": options.get(CONF_MODEL, data[CONF_MODEL]),
                    "system_prompt": options.get(CONF_PROMPT, DEFAULT_PROMPT),
                    "messages": messages,
                    "web_search": bool(options.get(CONF_WEB_SEARCH, False)),
                },
            )
            answer = payload.get("answer")
            if not isinstance(answer, str) or not answer.strip():
                raise HomeAssistantError("Duck.ai returned an empty answer")
        except HomeAssistantError as exc:
            _LOGGER.warning("Duck.ai conversation failed: %s", exc)
            response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                "Duck.ai недоступен. Проверьте Bridge и журналы Home Assistant.",
            )
            return conversation.ConversationResult(
                response=response, conversation_id=chat_log.conversation_id
            )

        chat_log.async_add_assistant_content_without_tools(
            conversation.AssistantContent(agent_id=self.entity_id, content=answer)
        )
        return conversation.async_get_result_from_chat_log(user_input, chat_log)
