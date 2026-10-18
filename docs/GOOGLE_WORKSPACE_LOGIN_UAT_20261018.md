# Google workspace login — October 18, 2026

## Implementation and environment

The homepage links to `/login`. Existing Google users see only their authorized
workspaces, can open a workspace, switch accounts, or sign out. Demo entry links
to Google login, and personal project pages include a Workspaces link.
The public demo retains its separate Firebase app and expiring session.

Hosted preview: `login-preview---decision-radar-web-ngm5jlvo5q-as.a.run.app`.
It calls the private API's `login-preview` revision, with existing Cloud Run
invoker permissions and the existing named Firestore database. No memberships,
project roles, Drive grants or Google API scopes were changed.

The app's owned login-preview and judge-preview hosts were added to Firebase's
Google sign-in domain list; all pre-existing authorized domains were preserved.

## Checks completed

- Lint and TypeScript checks passed.
- All 12 web tests passed.
- Backend: 177 tests and 46 subtests passed; 19 emulator-dependent tests skipped.
- Focused discovery checks cover valid memberships, an account without access,
  invalid roles, implicit parent project documents, non-Google sessions, missing
  authentication and no membership writes.
- Both production container builds succeeded.
- Hands-on: the homepage Google login entry opens `/login`, which explains Gmail
  and Workspace account support and provides the normal Google account picker.
- A cancelled sign-in displays a plain-language message and allows another try.
- Hosted health returned 200. Workspace discovery and direct project membership
  requests without authentication both returned 401 with `private, no-store`.

## Authenticated hands-on UAT

The user completed Google's account selection manually after the browser approval
review service could not inspect accounts.google.com due to its usage limit.
Early attempts returned the SDK's cancellation message; a later attempt succeeded
with no code changes. The cause of the earlier failures was not established.
No redirect or Firebase Hosting changes were made.

- Verified the login page showed **maxxinggemini@gmail.com** and only the existing
  **Real data testing** workspace, with **Administrator** access.
- Opened that workspace and loaded its actual Drive connection and two source
  documents from the real API. No private project data was edited.
- Used **Workspaces** to return to the chooser without signing in again.
- Entered the public demo in the same tab. It showed the separate demo identity,
  the sample folder, and its three source documents.
- Signed out of the demo, followed its Google-login link, and verified that the
  original personal Google session and workspace access were still present.
- Signed out of the personal Google session and verified the login screen returned.

## Homepage action layout

After the user requested clearer homepage spacing, the final web build aligned
both actions in two columns with separate helper text. Hosted desktop UAT measured
both buttons at 276 by 54 pixels with an 18-pixel horizontal gap. Both links were
clicked: Google opened the normal sign-in page, and the demo opened passwordless
entry. The rendered page was inspected and a screenshot retained. Narrow-screen
stacking is implemented in CSS but was not manually resized during this UAT.

The final layout change touches only the homepage and CSS; Google authentication
and the API are the same implementation verified above.

## Limits and release

A second Google identity was not used; no-access and invalid-role behavior has
backend test coverage. No Google account credentials were entered by the agent.
The user-completed OAuth return and real workspace reads passed on the hosted
preview. Main release and post-release checks are recorded in PR #36.
