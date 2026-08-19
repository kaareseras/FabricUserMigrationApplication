#!/bin/sh
set -eu

database="/app/data/fabric-access.db"
snapshot="/app/artifacts/fabric-permission-discovery"

mkdir -p "$snapshot" "$(dirname "$database")" "${AZURE_CONFIG_DIR:-/app/.azure}"

if [ "${FORCE_SNAPSHOT_IMPORT:-false}" = "true" ] || [ ! -f "$database" ]; then
    echo "Initializing the dashboard database from $snapshot"
    python server/import_snapshot.py --source "$snapshot" --database "$database"
fi

exec "$@"