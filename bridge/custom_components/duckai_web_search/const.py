"""Constants for the Duck.ai integration."""

DOMAIN = "duckai_web_search"

CONF_URL = "url"
CONF_MODEL = "model"
CONF_PROMPT = "system_prompt"
CONF_TYPE = "entry_type"
CONF_NAME = "name"
CONF_LLM_HASS_API = "llm_hass_api"

# Two independent kinds of config entries.
TYPE_TOOLS = "tools"  # LLM API (tool calling) for other conversation agents
TYPE_AGENT = "agent"  # Standalone Duck.ai conversation agent

UNIQUE_ID_TOOLS = "duckai_web_search"
DEFAULT_AGENT_NAME = "Duck.ai"
DEFAULT_TOOLS_NAME = "Duck.ai Web Search"
DEFAULT_URL = "http://127.0.0.1:8787"  # add-on port is published on the host

MAX_MESSAGES = 40
MAX_TOOL_ITERATIONS = 8

DEFAULT_PROMPT = (
    "Ты полезный голосовой ассистент Home Assistant. Отвечай на языке пользователя, "
    "кратко и точно. Не утверждай, что выполнил действие, если инструмент не подтвердил результат."
)
