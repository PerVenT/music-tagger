#!/bin/sh
set -e

TARGET_CONFIG="/config/config.yaml"
TEMPLATE_CONFIG="/app/templates/beets_default.yaml"

# Перевірка наявності конфігураційного файлу Beets
if [ ! -f "$TARGET_CONFIG" ]; then
    echo "[INIT] Beets config not found at $TARGET_CONFIG. Injecting default template..."
    cp "$TEMPLATE_CONFIG" "$TARGET_CONFIG"
else
    echo "[INIT] Existing Beets config detected at $TARGET_CONFIG."
fi

# Передаємо керування основному процесу (CMD) через exec
exec "$@"