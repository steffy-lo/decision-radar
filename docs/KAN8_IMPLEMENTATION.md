# KAN-8 job foundation

The KAN-8 branch now includes merged KAN-4, KAN-16, KAN-17, KAN-18/21 and
KAN-9/19 changes. The refresh and assessment services are present, but their
idempotent worker handlers and UI dispatch wiring are still pending. Normal
refresh/analysis job admission remains closed until that integration passes.

## Implemented boundary

- `POST /api/v1/projects/{project_id}/jobs`: immutable `kind`, `target_id`,
  and `source_version`; returns a project-scoped status receipt.
- `GET /api/v1/projects/{project_id}/jobs`: latest 50 receipts, including failures.
- `GET /api/v1/projects/{project_id}/jobs/{id}`: status lookup. For dispatched,
  unfinished work it checks Cloud Tasks; a missing task becomes a visible
  `delivery_exhausted` failure. Provider outages do not imply exhaustion.
- `POST /api/v1/projects/{project_id}/jobs/{id}/retry`: takes the displayed
  `generation`. Concurrent/repeated clicks reuse the next generation.
- Private worker `POST /tasks/execute`: validates Google's OIDC token audience
  and the configured verified service-account email before trusting delivery
  metadata. The browser API does not expose worker routes.
- Sources shows queued, running, retrying, completed and failed work. Admins
  can retry refresh jobs; editors/admins can retry analysis jobs; viewers can
  inspect status. Active work refreshes its status every five seconds.

Job IDs hash `(project_id, kind, target_id, source_version)`. Cloud Tasks names
append a retry generation. Completed receipts record the task name and source
version. A repeat submission returns the same receipt; manual retry keeps the
same immutable input and publication identity with a new delivery name.

Cloud Tasks owns the retry policy. The configured queue allows 100 total
attempts, including the initial delivery; the application imposes no separate
attempt cap. The worker records `retrying` and returns 503 on handler failure.
Once Cloud Tasks removes an unfinished task after exhausting delivery, the
next job detail/status read records `failed` with `delivery_exhausted`, enabling
manual retry. Only fixed error codes are stored or returned.

## Queue and worker configuration

Install `services/radar/requirements.txt`. Set `CLOUD_TASKS_LOCATION`,
`CLOUD_TASKS_QUEUE`, `TASK_WORKER_URL`, and `TASK_SERVICE_ACCOUNT_EMAIL` in the
service environment. The worker URL must use HTTPS. `TASK_WORKER_AUDIENCE`
defaults to that URL; set it explicitly to the receiving Cloud Run service URL
when task routing uses another URL. `npm run dev:worker` now serves HTTP on
port 8001 instead of running a placeholder loop.

Provision the queue separately; API startup does not change cloud infrastructure:

```sh
gcloud tasks queues create radar-jobs \
  --location=REGION --project=PROJECT_ID \
  --max-attempts=100 --max-retry-duration=0s \
  --min-backoff=10s --max-backoff=300s --max-doublings=3
```

Use `gcloud tasks queues update` with the same flags for an existing queue.
The adapter neither changes nor restricts the queue's retry settings. The API
identity needs Cloud Tasks Enqueuer plus task lookup permission and
`iam.serviceAccounts.actAs` on the delivery account. The delivery account needs
Cloud Run Invoker on the private worker. The worker needs the same Firestore,
Drive-token and extraction permissions as its eventual business handlers.
Keep these identities and credentials in cloud configuration, outside the repo.

The platform policy and callback headers follow Google's
[retry configuration](https://docs.cloud.google.com/tasks/docs/reference/rest/v2/RetryConfig)
and [HTTP task handler documentation](https://docs.cloud.google.com/tasks/docs/creating-http-target-tasks#http_target_tasks).

## Dependency integration still required

1. Register `refresh` and `analysis` handlers in `worker/handlers.py` in the
   same implementation/test track. They receive the saved immutable `Job`.
2. For a folder refresh, use one stable request version per user action and
   reuse it on repeat submission. Fetch Drive content at execution time and
   preserve KAN-4's native file IDs, modified versions and stable source IDs.
   A later refresh action uses a new request version so changed files are read.
3. For analysis, use a fingerprint covering the source snapshots and confirmed
   decision revisions. Load exactly that manifest or fail rather than silently
   analyze newer inputs. KAN-17 publication must keep stable finding/alert IDs
   and preserve existing human review dispositions.
4. Route the existing KAN-4 refresh and KAN-17 assessment controls through this
   job service and display the returned status. The foundation adds no fake
   refresh or analysis button to the product.
5. Run full UAT through the merged KAN-3 connection: root Doc, TXT, nested Doc,
   saved Meet transcript, changed-file refresh, duplicate submission, transient
   failure, exhausted retries and manual retry. Also test real Cloud Tasks OIDC
   delivery to the private worker, including an infrastructure failure that
   prevents a handler callback.

## Reliability limits

[Cloud Tasks can deliver more than once](https://docs.cloud.google.com/tasks/docs/common-pitfalls#duplicate_execution).
A completion receipt suppresses later deliveries after success, but does not
make business side effects atomic. Handlers **must** publish evidence/findings/
alerts with stable IDs derived from the saved input, including overlapping
callbacks and a crash after publication but before the completion receipt.
That guarantee must be verified against KAN-4/KAN-17 before KAN-8 is complete.

Dispatch is direct, with no transactional outbox, distributed lease engine,
periodic reconciliation process or stage-timeout framework. An interrupted
first dispatch can be repaired by resubmitting the same request. A dispatch
error produces a visible failed receipt. An unfinished dispatched task that
vanishes from Cloud Tasks is marked failed on the next detail/status read.
A request interrupted before dispatch confirmation requires resubmission;
there is deliberately no background recovery process for that gap.

## Initial verification on 3 October 2026 (before queue-controlled retries)

- 37 radar service/API tests passed, including authorization, three-attempt
  exhaustion, duplicate delivery, failure after publication, unavailable
  handlers, and repeat manual retry. The emulator test is skipped during this
  default run and executed separately.
- The separate Firestore emulator integration test passed: eight concurrent
  identical submissions persisted one job and one publication; eight concurrent
  manual retry requests advanced the failed job to generation 2 once. The first
  run exposed competing admission transaction locks; atomic create and avoiding
  redundant status writes corrected that failure.
- Six shared Python contract tests and three Node contract tests passed.
- Web lint, TypeScript checking, and the production Webpack build passed.
- Hands-on Chrome UAT used the actual Sources page, Firebase Auth emulator,
  real Firestore emulator storage, synthetic project membership and a synthetic
  task queue/handler. Signed in through the emulator Google popup, inspected
  the failed state at attempt 3, clicked Retry work, saw queued work advance to
  completed at attempt 1, refreshed status, and verified the completed receipt
  persisted. Repeated with the final service code and a second input version.
- With the controlled membership changed to viewer, status remained visible and
  the Retry work control disappeared. Restoring admin membership restored the
  control. Backend tests also reject viewer retry and editor folder refresh.
- Emulator inspection found two completed generation-2 job receipts for two
  different input versions and exactly two publication records. Failures and
  manual retries kept one publication per input version.

This UAT does not exercise Google Drive, Gemini, real assessment publication,
Cloud Tasks backoff scheduling, or real OIDC delivery. Those checks remain in
KAN-4/KAN-16/KAN-17 integration and cloud delivery UAT. Job admission on normal
`main` configuration remains closed with a clear 409 while handlers are absent.

The knowledge graph was updated with `graphify update .` (AST only). Its
community names now follow the rebuilt structural graph; semantic document
extraction and paid labeling were not run.

## Queue-controlled retry verification on 3 October 2026

- Removed the queue-policy rejection and the worker's three-attempt limit.
  Cloud Tasks now controls delivery exhaustion. Attempt counts remain in the
  job receipt for diagnostics and are hidden from the Sources UI.
- 38 radar service/API tests passed; the separately enabled emulator test was
  skipped in that suite. Tests cover 100 consecutive handler failures returning
  retry responses, task removal becoming a failed receipt, late callbacks,
  generation-safe manual retry, and success on attempt five with one stable
  publication. Web lint and TypeScript checking passed.
- Hands-on Chrome UAT used the actual Sources page with Auth/Firestore emulators
  and a synthetic queue/handler. A job exhausted 100 deliveries; Sources showed
  `Failed`, `Attempts: 100`, and `Retry work`. Clicking retry completed generation
  two on its first attempt; reloading preserved the completed receipt.
- This does not verify real Cloud Tasks timing, OIDC, Drive, or Gemini delivery.
  Those remain cloud integration UAT requirements. Changes remain local.
- Follow-up UI check: removed the attempt count from Sources. Opened the actual
  page and clicked Refresh status; the completed job remained visible without
  an attempt count. Component lint passed. Cloud Tasks still controls retries.
