# Cloud Run web deployment

The Next.js frontend runs as a public Cloud Run service. Its same-origin API
proxy forwards the user's Firebase ID token to the private API in
`Authorization` and authenticates the web service itself with a Cloud Run ID
token in `X-Serverless-Authorization`. The browser never receives the service
token.

## Build

`apps/web/Dockerfile` builds the standalone Next.js server. Set the four
`_FIREBASE_*` Cloud Build substitutions in `apps/web/cloudbuild.yaml` from the
Firebase **web app configuration** for this project. These `NEXT_PUBLIC_*`
values are embedded at build time; they are public client configuration, not
the Google Drive OAuth client secret. Do not put that secret in the web image.

## Runtime

Use a dedicated web service account with `roles/run.invoker` on the **API
service only**. Set `RADAR_API_URL` and `RADAR_API_AUDIENCE` to the API's HTTPS
Cloud Run URL. Keep the API private. The web service itself can be public once
Firebase Authentication and the API authorization path have been verified.

Add the deployed web hostname to Firebase Authentication authorized domains
before trying Google sign-in. The Google provider must be enabled. Configure
Google Drive OAuth redirect URLs separately; the Firebase sign-in provider
does not configure the Drive connection.

## Verification gate

Open the deployed URL in a browser. Sign in with Google, load a project through
the same-origin API proxy, and inspect the API response and saved data. Then
exercise a Drive connection and refresh, Vertex extraction, assessment, and
review with synthetic data. Check a failure and retry state. Record the actual
revision, data, and limitations in the PR. Do not merge on build or fixture
tests alone.
