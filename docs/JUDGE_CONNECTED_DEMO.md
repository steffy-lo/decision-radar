# Connected judge workspace

The `/judge` entry point opens the workspace configured by the web service's
`JUDGE_PROJECT_ID` environment variable. Set it to
`proj_e2e_rehearsal2_20261017` for the current connected sample workspace.
The homepage links to this entry point. The fixed fixture walkthrough remains
available separately.

The judge signs in with a Firebase email/password account supplied privately
with the submission. This is an application account, with no Google mailbox.
Email/password sign-in is enabled in Firebase; Google sign-in remains available.
Do not put the password, Firebase tokens, or Drive grants in this repository.

The current account has editor membership in this workspace only. Its trusted
Firestore membership also has `refresh_folder_id` set to the configured sample
folder. The API returns this optional capability as `refreshFolderId`.
Memberships without the capability keep their existing permissions. Viewers
cannot use it. Refresh submission, generic job submission, and manual retry
check both the explicitly granted folder and the currently selected folder
before reading Drive or submitting work. Only admins can change folders,
authorize, reconnect, or disconnect Drive. Direct synchronous refresh remains
admin-only. The existing Drive grant stays in Secret Manager; it is not copied
or disclosed to the judge.

The folder contains three actual Google Docs with synthetic project content.
The app reads them through its existing OAuth connection and saves source
snapshots. Gemini extraction, assessment, review, and retained decision history
use the actual backend services. Opening a Google Doc outside the app still
requires that Google account's own Drive access.

## Judge walkthrough

1. Open `/judge` and sign in using the supplied application credentials.
2. In Connections, click **Refresh folder**. The folder ID is locked for the judge.
3. In Decisions, create a test draft using **Decision record - Acme launch**.
   Copy the exact original commitment quote shown in the source text. Use an
   original required-by date of **2026-10-15**, entity **vendor_acme**, and predicate
   **delivery_date**. Confirm the decision to enable monitoring.
4. In Sources, select the new assumption. Use subject **Acme Logistics** and
   change **delivery date**. Click **Extract with Gemini** on **Acme Logistics
   vendor update**. It should publish the quoted **2026-10-24** date. If extraction
   is unresolved, inspect its explanation and retry rather than treating it as
   a verified fact.
5. In Reviews, run an assessment. Open the new decision's nine-day delay and
   submit a response with a rationale. Existing reviewed alerts are history;
   creating a new test decision gives the judge a fresh review to try.
6. Archive the test decision when finished. The shared workspace retains edits
   and audit history between visits; it does not reset automatically.

## Deployment and access management

Deploy both API and web changes, and set `JUDGE_PROJECT_ID` on the web service.
The optional capability is provisioned directly in the trusted membership
document, not accepted from request bodies or token claims. Remove the
membership or disable the Firebase account to end judge access. Removing
`refresh_folder_id` alone ends folder-refresh access while retaining normal
editor functionality. An administrator changing the selected folder must
explicitly update delegated access before that account can refresh again.
