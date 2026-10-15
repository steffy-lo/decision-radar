# Decision Radar deployment and recovery runbook

This runbook covers the Cloud Run staging stack in `geminimaxxing-509705`,
`asia-southeast1`. It is also the checklist for a clean project. Run commands
from a committed repository checkout; never put OAuth secrets or refresh tokens
in the repository, image, build substitutions, or command history.

## Services and ownership

| Service | Exposure | Runtime identity | Purpose |
| --- | --- | --- | --- |
| `decision-radar-web` | Public | `decision-radar-web@...` | Next.js and same-origin API proxy |
| `decision-radar-api-staging` | Cloud Run IAM private | `decision-radar-api-staging@...` | Firebase/project authorization and job admission |
| `radar-worker-dev` | Cloud Run IAM private | `radar-worker-runtime@...` | Cloud Tasks callbacks, Drive refresh, assessment |

The worker uses a separate runtime identity with Firestore access, source
snapshot bucket object access, and access to individual connection secrets.
Verify each new project secret grants this worker `secretAccessor` before its
first refresh; the API identity needs its own secret metadata and version
permissions for OAuth. Review whether assessment needs Vertex permissions
under the worker identity before a production release. The web identity has Invoker
on the API service. `radar-task-invoker@...` has Invoker on the worker. Do not
grant either private service `allUsers` access.

## Clean-project prerequisites

1. Enable Cloud Run, Cloud Build, Artifact Registry, Firestore, Cloud Tasks,
   Firebase Authentication, Secret Manager, Cloud Storage, Drive, Sheets, and
   Vertex AI APIs. Enable Pub/Sub and Cloud Scheduler before the Meet event and
   subscription-renewal track is deployed. As of 14 October, Meet, Workspace
   Events, Pub/Sub, and Scheduler APIs are enabled in the staging project.
   On 15 October, the isolated KAN-7 worker ingested a nonempty real Meet
   transcript through Pub/Sub. Replaying the event kept one source version,
   an empty transcript was acknowledged without an endless retry, and the
   Scheduler renewed the subscription. On 15 October, the standard worker
   revision `radar-worker-dev-00012-trj` ran under its separate identity and
   completed a first-time, browser-initiated Drive crawl of 11 sources.
2. Create a Firestore Native database named `decision-radar`, a private source
   snapshot bucket, an Artifact Registry Docker repository, and a Cloud Tasks
   queue named `radar-jobs` in `asia-southeast1`. Give the API and worker
   identities the permissions their adapters require. Verify project IAM and
   secret-level IAM separately; a human's Secret Manager Admin role does not
   grant a service account runtime access.
   Before first OAuth authorization for each project and connection kind,
   create `decision-radar-drive-<project-id>` or
   `decision-radar-meet-<project-id>` in Secret Manager. Grant the API runtime
   identity `secretAccessor`, `secretVersionManager`, and `viewer` on that
   individual secret. The staging API identity has no project-wide Secret
   Manager create permission. On 15 October, a new-project Drive callback
   returned `storage_unavailable` until its secret and bindings were created;
   retrying authorization then succeeded. Keep this bootstrap in the trusted
   project-provisioning process instead of granting the runtime broad access
   to every project secret.
3. Set up Firebase Google sign-in and add the public web hostname to its
   authorized domains. Configure the separate Google Drive OAuth client with
   the exact public `/oauth/google/callback` redirect URI. Store its client
   secret in the API runtime configuration, never in Next.js build arguments.
4. Set the API and worker environment from `services/radar/.env.example` and
   the web environment from `apps/web/.env.example` plus
   `docs/CLOUD_RUN_WEB_DEPLOYMENT.md`. The three services must use the same
   `FIREBASE_PROJECT_ID` and `FIRESTORE_DATABASE_ID=decision-radar`. Point
   Cloud Tasks at the private worker URL and use its dedicated delivery
   identity for OIDC. Set `RADAR_WEB_ORIGIN` to the public HTTPS origin so the
   OAuth callback does not redirect to the container's internal host.

## Reproducible image build and release

Use a fresh temporary build context from a reviewed commit. This prevents
local `.env`, virtual environments, generated graph files, and unstaged edits
from entering Cloud Build. The root Dockerfile-specific ignore files reduce
the final Docker context further.

```bash
git fetch origin main
git checkout <reviewed-commit>
mkdir -p /tmp/radar-api-build /tmp/radar-web-build
git archive HEAD services/radar Dockerfile.api Dockerfile.worker \
  cloudbuild.api.yaml cloudbuild.worker.yaml | tar -x -C /tmp/radar-api-build
git archive HEAD apps/web fixtures | tar -x -C /tmp/radar-web-build
```

Build the API and worker with `cloudbuild.api.yaml` and
`cloudbuild.worker.yaml` from `/tmp/radar-api-build`. Build the web image with
`apps/web/cloudbuild.yaml` from `/tmp/radar-web-build`, passing the four
Firebase **public web-app** substitutions in that config. Tag images with the
reviewed commit SHA. A successful Cloud Build is necessary but does not
replace the browser UAT gate.

Deploy API and worker images to their private Cloud Run services, then deploy
the matching web image. Confirm the new revision is Ready and serving 100%
traffic. A normal `gcloud run deploy SERVICE --image=IMAGE` preserves the
service's existing environment and IAM policy; check both before a clean
first deployment. The worker and API must agree on queue, worker URL,
audience, and Firestore database. Do not expose the API or worker publicly to
make a health check pass.

## Release checks

Set the three URLs and run `scripts/check-staging-health.sh`. It requires HTTP
200 from the public homepage and same-origin API health, and HTTP 403 from
unauthenticated direct API and worker requests. Then sign in through the
deployed web app and verify a synthetic project through the real Drive,
Cloud Tasks, Firestore, extraction, assessment, graph, and review path. Test
invalid folder access and correction, a failed job/retry, and the resulting
stored data. Record build IDs, revision IDs, job IDs, counts, and limits in the
feature PR. Recheck the integrated path after dependency merges.

For a quick read-only status check:

```bash
gcloud run services list --region=asia-southeast1 --project=geminimaxxing-509705
gcloud tasks queues describe radar-jobs --location=asia-southeast1 --project=geminimaxxing-509705
gcloud firestore databases list --project=geminimaxxing-509705
```

Staging queue configuration checked on 12 October 2026: three total attempts,
10-second minimum backoff, 300-second maximum backoff. Older worker notes
mention 100 attempts; the live queue setting takes precedence. A retry after
the source changes must create a new manifest/job, because a failed job is
bound to its original input version.

## Incident response and rollback

1. **Web/API health failure:** Identify the first unhealthy revision in Cloud
   Run and compare its image SHA and configuration with the last healthy
   revision. Route traffic back to the last healthy revision with Cloud Run's
   traffic control. Verify same-origin health and the signed-in project path.
2. **Worker delivery failure:** Inspect the job status in Connections or
   Sources and Cloud Tasks delivery logs. Fix configuration, IAM, or the source
   input. Retry a failed job only when its immutable input is still valid; if
   the source changed, start a new refresh. Do not manually mark a job
   completed. Check Firestore data and the next assessment after recovery.
3. **Drive grant failure:** The admin uses Reconnect Drive in the deployed app.
   Confirm the OAuth return reaches the public hostname, the connection is
   `active`, and a fresh folder refresh completes. If token storage fails,
   check that the project's Drive secret exists and that the API identity has
   its secret-level metadata and version permissions. The browser may show
   `needs_reconnect` after a storage failure; provision the secret and retry.
   A reconnect may rotate the refresh token; do not copy it into logs.
4. **Firestore or source snapshot failure:** Stop submitting new work, inspect
   service identity permissions and database/bucket availability, then retry
   the failed input after service recovery. Preserve immutable versions and
   audit history; do not overwrite them to make the UI appear healthy.
5. **Demo fallback:** Open the public homepage's **Explore demo workspace**
   link. It uses the bundled synthetic vendor-delay fixture and can explain
   the decision, cited change, and impact graph without Google APIs. It is a
   read-only fallback, not proof of live ingestion or durable review/export.

## Measurement and current limits

The design target for assessment is under 60 seconds at p95 for at most ten
decisions and 20,000 characters. Five completed, non-reused Cloud Tasks
analysis jobs in the isolated rehearsal project on 9 and 12 October took
7.4, 8.5, 19.5, 25.2, and 26.7 seconds from saved `created_at` to
`updated_at` (nearest-rank sample p95: 26.7 seconds). This small sample meets
the target but is not a load or end-to-end freshness measurement. Reused
completed jobs have no new worker duration. Native Meet freshness and
automatic Drive change capture remain unmeasured; the current Drive path is
manual refresh.

On 14 October, the health script again returned 200 for public web and its
same-origin API proxy, and 403 for direct unauthenticated API and worker
requests. The worker identity was split on 15 October. Its first revision
failed deployment because an existing OAuth client secret was injected as an
environment secret without `secretAccessor`; the narrow secret grant allowed
revision `00012-trj` to become Ready. A fresh Cloud Tasks refresh then
completed and populated 11 Drive sources in a separate test project. The
`decision-radar-meet-events` topic, `decision-radar-meet-events-kan7-uat`
subscription, and enabled `decision-radar-meet-renewal-kan7-uat` Scheduler job
were exercised with a real transcript, duplicate event, empty transcript, and
subscription renewal on 15 October. KAN-7 is merged. The full KAN-12/25
platform rehearsal still needs a clean integrated deployment and a post-deploy
browser pass covering extraction, assessment, graph, and review under the new
worker identity.
