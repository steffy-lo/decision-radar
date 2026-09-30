# Real Drive integration UAT

## Test setup

- Local integration checkout: `codex/kan3-4-16-17-real-drive-e2e` at `c8fc850`.
- Firebase Auth and Firestore emulators: `decision-radar`.
- App: `http://localhost:3004/projects/proj_kan41617_uat/sources`.
- Google Cloud project for OAuth and Vertex: `geminimaxxing-509705`.
- Synthetic Drive folder: `https://drive.google.com/drive/folders/1uc4D6a_jXKJxfJOq1gecBeCDmPtN8W9a`.
- The folder contains a root Google Doc, root TXT file, saved Meet-style transcript Doc, and a nested Google Doc and TXT file. All content is synthetic and the folder is not shared.
- Local test OAuth client redirects to `http://localhost:3004/oauth/google/callback`. Its secret is outside the repo.

## Checks completed

- PR #7 conflict resolution was pushed and GitHub reports `MERGEABLE` and `CLEAN`.
- The integrated branch passes web lint, Next.js production build, and 56 Python tests (37 core and 19 radar service tests).
- The Sources page was opened and clicked through in the browser. The synthetic emulator project shows the Drive connection control, monitored assumption, alias inputs, and empty source library.
- The Drive folder and nested folder were listed through the connected Drive account. The native Docs were read back and contain the expected baseline and October 24 vendor update text.

## Live pass pending

The OAuth app is in Testing mode. `umalimike36@gmail.com` is not yet on its test-user list. Add that account after user approval, complete Google Drive read-only consent, then click through:

1. Connect Drive and verify the app returns to the project Sources page with an active connection.
2. Enter folder ID `1uc4D6a_jXKJxfJOq1gecBeCDmPtN8W9a` and refresh. Verify all five supported files, including the nested Doc and TXT, appear. Refresh again and verify they are unchanged.
3. Use trusted entity `vendor_acme` with source wording `Acme Logistics`, and trusted predicate `delivery_date` with source wording `delivery date`. Extract from the vendor update and verify the quote and October 24, 2026 date against the source snapshot.
4. Run assessment on Reviews. Verify the October 15 baseline is contradicted by the October 24 update and inspect the alert in the browser.

Do not mark the real OAuth, Drive ingestion, or full end-to-end flow as passed until those clicks and results are observed.
