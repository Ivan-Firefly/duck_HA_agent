# Duck.ai Bridge

Local HTTP bridge to Duck.ai **and** automatic installer of the *Duck.ai* Home Assistant integration.

## What happens on start
1. The integration is copied to `/config/custom_components/duckai_web_search` (only when it is missing or changed).
2. If files were installed or updated, Home Assistant is restarted once so it can load them
   (option **auto_restart_ha**; turn it off to restart manually).
3. The bridge starts on port `8787`.

## After the first start
Settings → Devices & services → Add integration → **Duck.ai**. Bridge URL: `http://127.0.0.1:8787`
(or `http://<HA_LAN_IP>:8787`).

Endpoints: `GET /models`, `POST /search`, `POST /chat`.

The bridge has **no authentication**. Do not expose port 8787 to the internet.
