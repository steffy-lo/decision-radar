# Cloud Run deployment UAT — 9 October 2026

Project: `geminimaxxing-509705`, region: `asia-southeast1`.

- Web revision `decision-radar-web-00002-2g7` serves the public Cloud Run URL.
  The first revision failed because the container expected `server.js` at the
  wrong path. The fixed build uses an explicit Next.js tracing root and checks
  the standalone server path in Cloud Build.
- API revision `decision-radar-api-staging-00003-fj5` runs the current merged
  FastAPI code with the named `decision-radar` Firestore database. It remains
  private. The web service account has Invoker on that API service only.
- The deployed homepage and `/api/v1/health` through the web proxy returned
  HTTP 200. In Chrome, Mike signed in with Google and saw the synthetic demo
  decision register. This verifies the deployed browser sign-in and UI path.
- A live synthetic project's Sources page returned 401 from the API after
  sign-in. The API calls Firebase Admin with `check_revoked=True`; its runtime
  service account has no Firebase Authentication user-read role. A narrow
  `roles/firebaseauth.viewer` grant has been requested. The signed-in user's
  Firebase UID also differs from the older emulator member UID in this test
  project, so membership needs to be handled before live project UAT.
- The Cloud Run hostname was added to Firebase Authentication authorized
  domains. The same deployed callback was saved on the existing localhost UAT
  OAuth client. Google sign-in worked in Chrome. The in-app browser returned
  `auth/network-request-failed` during the popup flow; the external Chrome
  result is the browser UAT evidence for sign-in.

Still required before merging the deployment PR: resolve the live project
authorization, click through Drive connection and refresh against the
synthetic folder, verify the Cloud Tasks worker and Vertex result in the UI,
and test a failure and retry. The Google OAuth client is restricted to its
configured test users. This is a staging deployment and does not establish a
production-ready OAuth consent screen.
