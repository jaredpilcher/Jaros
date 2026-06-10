#!/bin/sh
set -e

# If a requirements.txt exists in the mounted tools folder, install it dynamically
if [ -f /data/tools/requirements.txt ]; then
    echo "=========================================================="
    echo "Installing dynamic tool dependencies from /data/tools/requirements.txt..."
    pip install --no-cache-dir -r /data/tools/requirements.txt
    echo "=========================================================="
fi

# If a requirements.txt exists in the mounted config folder, install it dynamically
if [ -f /app/config/requirements.txt ]; then
    echo "=========================================================="
    echo "Installing dynamic config dependencies from /app/config/requirements.txt..."
    pip install --no-cache-dir -r /app/config/requirements.txt
    echo "=========================================================="
fi

exec "$@"
