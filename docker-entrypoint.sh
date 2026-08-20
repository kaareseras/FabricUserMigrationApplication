#!/bin/sh
set -eu

database="/app/data/fabric-access.db"
snapshot="/app/artifacts/fabric-permission-discovery"

mkdir -p "$snapshot" "$(dirname "$database")" "${AZURE_CONFIG_DIR:-/app/.azure}"

if [ "${FORCE_SNAPSHOT_IMPORT:-false}" = "true" ] || [ ! -f "$database" ]; then
    echo "Initializing the dashboard database from $snapshot"
    python -m server.import_snapshot --source "$snapshot" --database "$database"
fi

exec "$@"