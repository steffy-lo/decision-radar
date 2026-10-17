#!/usr/bin/env bash
set -euo pipefail

: "${RADAR_PROJECT_ID:?Set RADAR_PROJECT_ID to the Decision Radar project ID}"

cloud_project="${GOOGLE_CLOUD_PROJECT:-geminimaxxing-509705}"
api_identity="${RADAR_API_SERVICE_ACCOUNT:-decision-radar-api-staging@${cloud_project}.iam.gserviceaccount.com}"
worker_identity="${RADAR_WORKER_SERVICE_ACCOUNT:-radar-worker-runtime@${cloud_project}.iam.gserviceaccount.com}"

if [[ ! "$RADAR_PROJECT_ID" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "RADAR_PROJECT_ID may contain only letters, numbers, hyphens, and underscores." >&2
  exit 2
fi

for kind in drive meet; do
  secret="decision-radar-${kind}-${RADAR_PROJECT_ID}"
  if ! gcloud secrets describe "$secret" --project "$cloud_project" --format='value(name)' >/dev/null 2>&1; then
    gcloud secrets create "$secret" --project "$cloud_project" --replication-policy=automatic --quiet
  fi
  for role in roles/secretmanager.secretAccessor roles/secretmanager.secretVersionManager roles/secretmanager.viewer; do
    gcloud secrets add-iam-policy-binding "$secret" --project "$cloud_project" \
      --member="serviceAccount:${api_identity}" --role="$role" --quiet >/dev/null
  done
  gcloud secrets add-iam-policy-binding "$secret" --project "$cloud_project" \
    --member="serviceAccount:${worker_identity}" \
    --role=roles/secretmanager.secretAccessor --quiet >/dev/null
  printf 'Provisioned %s with API and worker access.\n' "$secret"
done
