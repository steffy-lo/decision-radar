# Connected public demo

Open `/demo` and click **Try demo**. The read-only **Demo email** field is
prefilled with `demo@decision-radar.example`, a sample workspace label rather
than a mailbox. No password, email verification, or Google invitation is needed.
`/judge` redirects to `/demo`; the homepage links to `/demo`.

The owner explicitly approved public visitors refreshing the connected sample
folder, creating and archiving sample decisions, extracting facts with Gemini,
running assessments and saving reviews. This access applies only to the sample
workspace, not personal workspaces or other Drive folders.

## Session and access controls

Each visitor signs in with Firebase Anonymous Authentication and receives a
separate UID. The authenticated admission endpoint accepts only verified
anonymous identities and an empty request body. Project, role and folder cannot
be chosen by the client. A transaction grants editor membership only in the
configured demo project, with refresh access pinned to the configured folder.
It admits at most ten new sessions per minute across the workspace. Repeated
admission of the same UID is idempotent and does not extend access.

Access expires one hour after the Firebase identity was created. Every normal
project API request checks the server-side expiry, configured project, granted
folder and currently selected folder. Changing the selected folder blocks
existing visitor access as well as new admission. Existing memberships cannot
be promoted or overwritten by demo admission. Viewers and ordinary editors
retain their existing permissions. OAuth, folder selection and disconnect
remain admin-only. The Drive grant remains in Secret Manager.

The browser uses a separate named Firebase app for demo sessions and tab-session
persistence. Entering or signing out of the demo does not replace a personal
Google workspace sign-in. The UI returns to demo entry when its session expires;
the API enforces expiry independently of browser state. Membership records can
remain for audit purposes, but an expired record grants no API access.

This follows [Firebase's anonymous sign-in flow](https://firebase.google.com/docs/auth/web/anonymous-auth).
The API does not mint public custom tokens or reveal a shared account password.

## Runtime configuration

Enable Anonymous sign-in in Firebase Authentication. On the API service set:

- `DEMO_PROJECT_ID=proj_e2e_rehearsal2_20261017`
- `DEMO_FOLDER_ID=1PhXz4nT1Vikm81ATWuFciBpwMGkdByWO`

On the web service set the same `DEMO_PROJECT_ID`. Deploy both API and web.
Removing the API demo configuration disables admission and access for existing
public demo memberships. Deleting one visitor's membership revokes that
visitor's access. No new IAM signing permission or service-account key is needed.

## Walkthrough

1. Open `/demo` and click **Try demo**.
2. In Connections, click **Refresh folder**. The folder ID is locked.
3. In Decisions, create a test draft using **Decision record - Acme launch**.
   Copy an exact original commitment quote from the source text. Use original
   required-by date **2026-10-15**, entity **vendor_acme**, and predicate
   **delivery_date**. Confirm the decision.
4. In Sources, select the new assumption. Use subject **Acme Logistics** and
   change **delivery date**. Click **Extract with Gemini** on **Acme Logistics
   vendor update**. The confirmed update is **2026-10-24**. Inspect unresolved
   extraction results before retrying them.
5. In Reviews, run an assessment, inspect the nine-day delay, and submit a
   response with a rationale. A new test decision provides a fresh review;
   existing reviewed alerts remain history.
6. Archive the test decision when finished.

The three Google Docs are actual connected documents with deliberately
synthetic project content. Drive reads, Gemini extraction and saved app data use
real services. Separately opening a Google Doc requires the browser account's
own Drive permissions. This shared sample workspace retains edits and history
between visits and does not reset automatically.
