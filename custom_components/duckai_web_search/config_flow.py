"""Separate Duck.ai web-search tool and conversation-agent configuration flows."""
import asyncio
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector
from .const import DOMAIN, CONF_URL, CONF_MODEL, CONF_MODE, MODE_TOOL, MODE_AGENT, CONF_PROMPT, DEFAULT_PROMPT

MODES = [selector.SelectOptionDict(value=MODE_TOOL, label="Tool calling for other conversation agents"),
         selector.SelectOptionDict(value=MODE_AGENT, label="Standalone Duck.ai conversation agent")]

class DuckaiWebSearchFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self._bridge_url = None
        self._model_options = []
        self._mode = MODE_TOOL

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            self._mode = user_input[CONF_MODE]
            try:
                session = async_get_clientsession(self.hass)
                async with session.get(f"{url}/models", timeout=aiohttp.ClientTimeout(total=25)) as response:
                    response.raise_for_status()
                    payload = await response.json()
                models = payload.get("models", [])
                if not isinstance(models, list):
                    raise ValueError("Invalid models response")
                self._model_options = [selector.SelectOptionDict(value=m["id"], label=m.get("name") or m["id"])
                                       for m in models if isinstance(m, dict) and isinstance(m.get("id"), str) and m["id"]]
                if not self._model_options:
                    errors["base"] = "no_models"
                else:
                    self._bridge_url = url
                    return await self.async_step_model()
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError):
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required(CONF_MODE, default=self._mode): selector.SelectSelector(selector.SelectSelectorConfig(options=MODES, mode=selector.SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_URL, default=self._bridge_url or "http://homeassistant.local:8787"): str,
        }), errors=errors)

    async def async_step_model(self, user_input=None):
        if not self._bridge_url or not self._model_options:
            return await self.async_step_user()
        if user_input is not None:
            if user_input[CONF_MODEL] not in {m["value"] for m in self._model_options}:
                return self.async_show_form(step_id="model", data_schema=self._model_schema(), errors={"base": "invalid_model"})
            await self.async_set_unique_id(f"duckai_{self._mode}")
            self._abort_if_unique_id_configured()
            title = "Duck.ai Conversation Agent" if self._mode == MODE_AGENT else "Duck.ai Web Search Tool"
            return self.async_create_entry(title=title, data={CONF_URL: self._bridge_url, CONF_MODEL: user_input[CONF_MODEL], CONF_MODE: self._mode})
        return self.async_show_form(step_id="model", data_schema=self._model_schema())

    def _model_schema(self):
        return vol.Schema({vol.Required(CONF_MODEL): selector.SelectSelector(
            selector.SelectSelectorConfig(options=self._model_options, mode=selector.SelectSelectorMode.DROPDOWN))})

    @staticmethod
    def async_get_options_flow(config_entry):
        return DuckaiWebSearchOptionsFlow()

class DuckaiWebSearchOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        models = []
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(self.config_entry.data[CONF_URL].rstrip("/") + "/models",
                                   timeout=aiohttp.ClientTimeout(total=25)) as response:
                response.raise_for_status()
                models = (await response.json()).get("models", [])
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            pass
        options = [selector.SelectOptionDict(value=m["id"], label=m.get("name") or m["id"])
                   for m in models if isinstance(m, dict) and isinstance(m.get("id"), str) and m["id"]]
        current = self.config_entry.options.get(CONF_MODEL, self.config_entry.data[CONF_MODEL])
        if current not in {m["value"] for m in options}:
            options.append(selector.SelectOptionDict(value=current, label=current))
        fields = {vol.Required(CONF_MODEL, default=current): selector.SelectSelector(
            selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN))}
        if self.config_entry.data.get(CONF_MODE) == MODE_AGENT:
            fields[vol.Required(CONF_PROMPT, default=self.config_entry.options.get(CONF_PROMPT, DEFAULT_PROMPT))] = selector.TextSelector(
                selector.TextSelectorConfig(multiline=True, type=selector.TextSelectorType.TEXT))
        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields))
