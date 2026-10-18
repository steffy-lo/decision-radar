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

Google's account-selection page requires the user to complete it manually:
automatic browser approval review could not inspect accounts.google.com because
the review service reached its usage limit. The app-side checks can continue
after the user completes the normal Google flow.

Authenticated workspace access and session-isolation results will be recorded
in PR #36 after the user-completed Google sign-in is verified in the app.
