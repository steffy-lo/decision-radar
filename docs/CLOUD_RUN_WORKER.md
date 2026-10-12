# Deploy the worker continuously from GitHub

Cloud Run runs the private HTTP service in `services/radar/worker/tasks.py`.
The root `Dockerfile.worker` builds that service with Python 3.12. Its matching
ignore file admits Python service source and requirements, excluding local
environment settings, virtual environments, tests, web files, and credentials.

The deployment follows pushed commits on one selected branch. Local edits and
commits on other branches do not change the deployed revision. Build failures
leave the previously deployed revision in place. Source changes do not update
Cloud Run environment variables or IAM settings.

## Prerequisites

- Commit and merge the Dockerfile, its ignore file, and the KAN-8 HTTP worker
  implementation to the branch Cloud Run will follow. The old placeholder
  worker does not serve HTTP and cannot pass Cloud Run startup checks.
- Enable Cloud Build, Cloud Run, and Artifact Registry APIs in the real Google
  Cloud project. The project needs billing and the permissions required by
  Google's repository deployment setup.
- Create the `radar-task-invoker` delivery account and a separate worker runtime
  account with Firestore access. The delivery account needs Cloud Run Invoker
  on the service. Cloud Tasks and its delivery identity use the same project.

## Google Cloud Console setup

1. Open Cloud Run and click **Connect repository** for a new service. For an
   existing `radar-worker`, open its **Source** tab and click **Connect to repo**.
2. Select **Cloud Build**, authenticate with GitHub, and authorize the
   `steffy-lo/decision-radar` repository through the normal GitHub flow.
3. Select that repository. In build configuration, use branch `^main$` and
   build type **Dockerfile**. Set the source location to `Dockerfile.worker`.
   Because this Dockerfile is at the repository root, its build context is the
   repository root; `COPY services/radar ...` reads the current commit's code.
   Leave file filters unset to deploy every commit on the selected branch.
4. Use service name `radar-worker`, region `asia-southeast1`, container port
   `8080`, **Require authentication**, and **All** ingress. Leave command and
   arguments empty to use the Dockerfile entrypoint. Select the worker runtime
   service account in the Security settings.
5. Set the service environment variables:

   | Variable | Value |
   |---|---|
   | `FIREBASE_PROJECT_ID` | Actual Google Cloud/Firebase project ID |
   | `FIRESTORE_DATABASE_ID` | `decision-radar` for `geminimaxxing-509705` |
   | `GOOGLE_SECRET_MANAGER_PROJECT_ID` | Project holding the Drive connection secret, if different from `FIREBASE_PROJECT_ID` |
   | `CLOUD_TASKS_LOCATION` | `asia-southeast1`, matching the queue |
   | `CLOUD_TASKS_QUEUE` | `radar-jobs` |
   | `TASK_SERVICE_ACCOUNT_EMAIL` | Delivery account email |

   The image sets production mode, host `0.0.0.0`, and worker port `8080`.
   Emulator variables must be absent. Keep credentials outside the repository.
6. Create the service and wait for the first successful build and deployment.
   Copy its base HTTPS URL. Add `TASK_WORKER_URL` and `TASK_WORKER_AUDIENCE`,
   both equal to that URL, through **Edit & deploy new revision**. The adapter
   adds `/tasks/execute`; omit that path from these values.
7. Grant the delivery account **Cloud Run Invoker** on this service. Configure
   the local/API caller's queue permissions and delivery-account impersonation
   separately as described in `KAN8_IMPLEMENTATION.md`.
8. Put the same project, queue, service URL, audience, and delivery-account
   values in the API environment. For cloud integration testing, the API and
   worker must use the same cloud Firestore database rather than a local
   Firestore emulator.

Cloud Tasks controls retries; the application has no three-attempt cap. The
staging `radar-jobs` queue was configured for three total attempts on
12 October 2026. Failed handler callbacks return 503, and an
unfinished job becomes failed on the next status read after its task is removed.

For a development service that follows the current KAN-8 branch, use a separate
service such as `radar-worker-dev` and branch expression
`^codex/kan8-integrated-uat$` once that integration branch is pushed. Only
pushed commits will trigger deployment.
Use a separate test queue and point its API configuration to the development
service. The GitHub connection and build trigger are configured in Google
Cloud; adding the Dockerfile alone does not activate deployment.

## Verify a deployment

After an approved change lands on the selected branch, inspect Cloud Build's
build history and the Cloud Run revision details. Match the source commit to
the GitHub commit and confirm the new revision is Ready and receives traffic.
In worker logs, verify it starts listening on port 8080. Full job UAT also needs
real Cloud Tasks OIDC delivery and the integrated KAN-4/KAN-17 handlers.
The integrated KAN-8 branch registers refresh and analysis handlers, but their
real Cloud Tasks delivery has not passed UAT. The worker runtime identity also
needs read access to the saved Drive token in Secret Manager.

The image was built from an isolated source bundle through Cloud Build on
7 October 2026 and deployed as the private `radar-worker-dev` service. The
unauthenticated endpoint returned HTTP 403. A synthetic Cloud Tasks delivery
completed after the async dependency fix, including a nonempty assessment
that published two findings and one alert to named Firestore. Continuous
GitHub deployment and the real Drive/Gemini browser flow remain untested.

Reference: [Google's continuous deployment setup](https://docs.cloud.google.com/run/docs/continuous-deployment).
