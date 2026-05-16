#!/bin/bash
SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STDIN_PIPE="$SERVER_DIR/.server_stdin"

if [ -p "$STDIN_PIPE" ]; then
    echo "stop" > "$STDIN_PIPE"
else
    echo "[AeroServer] FIFO introuvable — le serveur est peut-être déjà arrêté."
fi
