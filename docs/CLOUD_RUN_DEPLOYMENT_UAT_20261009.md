# Cloud Run deployment UAT — 9 October 2026

Project: `geminimaxxing-509705`, region: `asia-southeast1`.

- Web revision `decision-radar-web-00003-gbk` serves the public Cloud Run URL.
  The first revision failed because the container expected `server.js` at the
  wrong path. The fixed build uses an explicit Next.js tracing root and checks
  the standalone server path in Cloud Build.
- API revision `decision-radar-api-staging-00004-8zg` runs the current merged
  FastAPI code with the named `decision-radar` Firestore database. It remains
  private. The web service account has Invoker on that API service only. The
  revision has the deployed web origin and OAuth callback, the existing OAuth
  client secret, and the `radar-task-invoker` delivery identity for Cloud Tasks.
- The deployed homepage and `/api/v1/health` through the web proxy returned
  HTTP 200. In Chrome, Mike signed in with Google and saw the synthetic demo
  decision register. This verifies the deployed browser sign-in and UI path.
- A live synthetic project's Sources page initially returned 401. Mike
  approved `roles/firebaseauth.viewer` for the staging API service account on
  this project; the grant is in place and `/me` now returns 200. The signed-in
  user's Firebase UID differed from the older emulator member UID, so the
  current UID was added as a project admin for this synthetic UAT project.
- The active Drive connection listed the original five synthetic files. A
  repeated refresh of unchanged inputs reused a completed job. Uploading
  `cloud-refresh-uat-20261009.txt` to the synthetic folder changed its manifest:
  the deployed UI showed a new queued, running, then completed folder job, and
  the sixth file appeared in Sources. An unavailable folder produced the
  expected access error; restoring the valid folder ID returned to completed.
- Clicking Extract with Gemini for `vendor-update.txt` returned HTTP 200 from
  the deployed API. Its verified October 24 delivery fact remained visible.
  Running assessment returned completed; Reviews showed the nine-day alert,
  and the impact graph showed the challenged decision plus two downstream
  decisions. These assessment inputs matched prior saved evidence, so the
  completed assessment job was reused.
- The Cloud Run hostname was added to Firebase Authentication authorized
  domains. The same deployed callback was saved on the existing localhost UAT
  OAuth client. Google sign-in worked in Chrome. The in-app browser returned
  `auth/network-request-failed` during the popup flow; the external Chrome
  result is the browser UAT evidence for sign-in.
- A fresh Drive reconnect reached Google's test-app warning. Mike asked Codex
  to continue past it. Automatic browser review blocked the final consent
  action because it detected a redirect to `https://0.0.0.0:8080` rather than
  the deployed host. The web callback had used the internal request URL as its
  redirect base. The fix requires a configured `RADAR_WEB_ORIGIN` in production
  and fails closed if it is missing. Its focused tests, lint, type check, local
  webpack production build, and Cloud Build passed. Revision `00003-gbk` now
  serves all web traffic with `RADAR_WEB_ORIGIN` set to the public host. A
  no-code callback probe returned HTTP 307 to that public host, and proxied
  API health returned 200. This verifies redirect construction, not a complete
  Google consent callback. Codex must not repeat the blocked browser action.

Still required before merging the deployment PR: finish a fresh Google Drive
OAuth callback through the deployed hostname, verify that reconnect preserves
the live connection, and exercise a failed Cloud Tasks delivery with its retry
control. The unavailable-folder test covered input failure and recovery, not
worker retry. The Google OAuth client is restricted to configured test users.
This is a staging deployment and does not establish a production-ready OAuth
consent screen.

After revision `00003-gbk` was deployed, Mike completed a fresh Google consent
return. The callback reached the private API but returned HTTP 503 while
storing the new refresh token. The API service account has Secret Accessor on
`decision-radar-drive-proj_oauth_pr10_uat_20261007`, but the token store also
reads secret metadata, adds a new version, and disables prior versions. An
exact, secret-scoped grant for those operations is pending approval. The
earlier token remains available for the successful refresh UAT above; the
fresh reconnect has not passed.
