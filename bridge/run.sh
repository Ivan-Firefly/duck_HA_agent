#!/bin/sh
node /app/install.js || echo "[duckai] integration install step failed (bridge keeps running)"
exec node /app/server.js
