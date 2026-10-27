"""Config flow: two independent setups — tool calling and conversation agent."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .bridge import DuckBridgeError, async_get_models
from .const import (
    CONF_MODEL,
    CONF_NAME,
    CONF_PROMPT,
    CONF_TYPE,
    CONF_URL,
    CONF_WEB_SEARCH,
    DEFAULT_AGENT_NAME,
    DEFAULT_PROMPT,
    DEFAULT_TOOLS_NAME,
    DEFAULT_URL,
    DOMAIN,
    TYPE_AGENT,
    TYPE_TOOLS,
    UNIQUE_ID_TOOLS,
)


def _model_options(models: list[dict[str, Any]]) -> list[selector.SelectOptionDict]:
    out = []
    for m in models:
        name = m.get("name") or m["id"]
        out.append(
            selector.SelectOptionDict(
                value=m["id"], label=name if name == m["id"] else f"{name} ({m['id']})"
            )
        )
    return out


def _model_selector(options: list[selector.SelectOptionDict]) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
    )


_PROMPT_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(multiline=True, type=selector.TextSelectorType.TEXT)
)


class DuckaiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        self._entry_type = TYPE_TOOLS
        self._bridge_url: str | None = None
        self._models: list[selector.SelectOptionDict] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return DuckaiOptionsFlow()

    # ---- menu -----------------------------------------------------------
    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        has_tools = any(
            e.data.get(CONF_TYPE, TYPE_TOOLS) == TYPE_TOOLS
            for e in self._async_current_entries()
        )
        options = [TYPE_AGENT] if has_tools else [TYPE_TOOLS, TYPE_AGENT]
        return self.async_show_menu(step_id="user", menu_options=options)

    async def async_step_tools(self, user_input: dict[str, Any] | None = None):
        self._entry_type = TYPE_TOOLS
        await self.async_set_unique_id(UNIQUE_ID_TOOLS)
        self._abort_if_unique_id_configured()
        return await self.async_step_bridge()

    async def async_step_agent(self, user_input: dict[str, Any] | None = None):
        self._entry_type = TYPE_AGENT
        return await self.async_step_bridge()

    # ---- shared: bridge URL ---------------------------------------------
    async def async_step_bridge(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            self._bridge_url = url
            try:
                models = await async_get_models(self.hass, url)
            except DuckBridgeError:
                errors["base"] = "cannot_connect"
            else:
                self._models = _model_options(models)
                if not self._models:
                    errors["base"] = "no_models"
                elif self._entry_type == TYPE_TOOLS:
                    return await self.async_step_tools_settings()
                else:
                    return await self.async_step_agent_settings()

        default_url = self._bridge_url
        if not default_url:
            default_url = next(
                (e.data[CONF_URL] for e in self._async_current_entries() if e.data.get(CONF_URL)),
                DEFAULT_URL,
            )
        return self.async_show_form(
            step_id="bridge",
            data_schema=vol.Schema({vol.Required(CONF_URL, default=default_url): str}),
            errors=errors,
        )

    # ---- tool calling settings ------------------------------------------
    async def async_step_tools_settings(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_MODEL] not in {o["value"] for o in self._models}:
                errors["base"] = "invalid_model"
            else:
                return self.async_create_entry(
                    title=DEFAULT_TOOLS_NAME,
                    data={
                        CONF_URL: self._bridge_url,
                        CONF_MODEL: user_input[CONF_MODEL],
                        CONF_TYPE: TYPE_TOOLS,
                    },
                )
        return self.async_show_form(
            step_id="tools_settings",
            data_schema=vol.Schema(
                {vol.Required(CONF_MODEL, default=self._models[0]["value"]): _model_selector(self._models)}
            ),
            errors=errors,
        )

    # ---- conversation agent settings ------------------------------------
    async def async_step_agent_settings(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_MODEL] not in {o["value"] for o in self._models}:
                errors["base"] = "invalid_model"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME].strip() or DEFAULT_AGENT_NAME,
                    data={
                        CONF_URL: self._bridge_url,
                        CONF_MODEL: user_input[CONF_MODEL],
                        CONF_TYPE: TYPE_AGENT,
                    },
                    options={
                        CONF_PROMPT: user_input[CONF_PROMPT],
                        CONF_WEB_SEARCH: user_input[CONF_WEB_SEARCH],
                    },
                )
        return self.async_show_form(
            step_id="agent_settings",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_AGENT_NAME): str,
                    vol.Required(CONF_MODEL, default=self._models[0]["value"]): _model_selector(self._models),
                    vol.Required(CONF_PROMPT, default=DEFAULT_PROMPT): _PROMPT_SELECTOR,
                    vol.Required(CONF_WEB_SEARCH, default=False): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )


class DuckaiOptionsFlow(config_entries.OptionsFlow):
    """Edit model (and prompt / web search for agents) without re-adding."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        entry = self.config_entry
        is_agent = entry.data.get(CONF_TYPE, TYPE_TOOLS) == TYPE_AGENT
        if user_input is not None:
            return self.async_create_entry(title="", data={**entry.options, **user_input})

        try:
            options = _model_options(await async_get_models(self.hass, entry.data[CONF_URL]))
        except DuckBridgeError:
            options = []
        current = entry.options.get(CONF_MODEL, entry.data[CONF_MODEL])
        if current not in {o["value"] for o in options}:
            options.append(selector.SelectOptionDict(value=current, label=current))

        schema: dict[Any, Any] = {
            vol.Required(CONF_MODEL, default=current): _model_selector(options)
        }
        if is_agent:
            schema[vol.Required(CONF_PROMPT, default=entry.options.get(CONF_PROMPT, DEFAULT_PROMPT))] = _PROMPT_SELECTOR
            schema[vol.Required(CONF_WEB_SEARCH, default=entry.options.get(CONF_WEB_SEARCH, False))] = selector.BooleanSelector()
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
