#!/bin/sh
set -eu

database="/app/data/fabric-access.db"
snapshot="/app/artifacts/fabric-permission-discovery"

if [ "${FORCE_SNAPSHOT_IMPORT:-false}" = "true" ] || [ ! -f "$database" ]; then
    if [ ! -f "$snapshot/workspaces.json" ] \
        && [ ! -f "$snapshot/powerbi-artifact-user-scans.ndjson" ] \
        && [ ! -f "$snapshot/powerbi-artifact-user-scans.json" ] \
        && [ ! -f "$snapshot/workspace-role-assignments.csv" ]; then
        echo "Snapshot database is missing and no discovery data is mounted at $snapshot" >&2
        exit 1
    fi

    python server/import_snapshot.py --source "$snapshot" --database "$database"
fi

exec "$@"