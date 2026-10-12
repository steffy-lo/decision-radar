#!/usr/bin/env bash
set -euo pipefail

: "${RADAR_WEB_URL:?Set RADAR_WEB_URL to the public Cloud Run URL}"
: "${RADAR_API_URL:?Set RADAR_API_URL to the private API Cloud Run URL}"
: "${RADAR_WORKER_URL:?Set RADAR_WORKER_URL to the private worker Cloud Run URL}"

check() {
  local label="$1" url="$2" expected="$3" actual
  actual="$(curl --silent --show-error --location --output /dev/null --write-out '%{http_code}' "$url")"
  printf '%s: HTTP %s (expected %s)\n' "$label" "$actual" "$expected"
  [[ "$actual" == "$expected" ]]
}

check 'Public web' "${RADAR_WEB_URL%/}/" 200
check 'Same-origin API health' "${RADAR_WEB_URL%/}/api/v1/health" 200
check 'Private API without identity' "${RADAR_API_URL%/}/health" 403
check 'Private worker without identity' "${RADAR_WORKER_URL%/}/health" 403
