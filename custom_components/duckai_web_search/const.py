"""Constants for the Duck.ai integration."""

DOMAIN = "duckai_web_search"

CONF_URL = "url"
CONF_MODEL = "model"
CONF_PROMPT = "system_prompt"
CONF_TYPE = "entry_type"
CONF_NAME = "name"
CONF_WEB_SEARCH = "web_search"

# Two independent kinds of config entries.
TYPE_TOOLS = "tools"  # LLM API (tool calling) for other conversation agents
TYPE_AGENT = "agent"  # Standalone Duck.ai conversation agent

UNIQUE_ID_TOOLS = "duckai_web_search"
DEFAULT_AGENT_NAME = "Duck.ai"
DEFAULT_TOOLS_NAME = "Duck.ai Web Search"
DEFAULT_URL = "http://192.168.1.100:8787"

MAX_TURNS = 12

DEFAULT_PROMPT = (
    "Ты полезный голосовой ассистент Home Assistant. Отвечай на языке пользователя, "
    "кратко и точно. Не утверждай, что управлял устройствами, если не выполнял никаких действий."
)
