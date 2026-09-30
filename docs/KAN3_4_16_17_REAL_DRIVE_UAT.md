# Real Drive integration UAT

## Test setup

- Local integration checkout: `codex/kan3-4-16-17-real-drive-e2e`.
- Firebase Auth and Firestore emulators: `decision-radar`.
- App: `http://localhost:3004/projects/proj_kan41617_uat/sources`.
- Google Cloud project for OAuth and Vertex: `geminimaxxing-509705`.
- Synthetic Drive folder: `https://drive.google.com/drive/folders/1uc4D6a_jXKJxfJOq1gecBeCDmPtN8W9a`.
- The folder contains a root Google Doc, root TXT file, saved Meet-style transcript Doc, and a nested Google Doc and TXT file. All content is synthetic and the folder is not shared.
- Local test OAuth client redirects to `http://localhost:3004/oauth/google/callback`. Its secret is outside the repo.

## Checks completed

- PR #7 conflict resolution was pushed and GitHub reports `MERGEABLE` and `CLEAN`.
- The integrated branch passes web lint, Next.js production build, and 56 Python tests (37 core and 19 radar service tests).
- The Sources page was opened and clicked through in the browser. The synthetic emulator project shows the Drive connection control, monitored assumption, alias inputs, and source library.
- The Drive folder and nested folder were listed through the connected Drive account. The native Docs were read back and contain the expected baseline and October 24 vendor update text.

## Live browser pass

`umalimike36@gmail.com` was confirmed on the OAuth test-user list. The user reviewed Google's test-app warning and completed Drive read-only consent. The app returned to Sources with an active connection.

1. Folder refresh scanned five files and created five sources: root Doc, root TXT, saved Meet-style transcript Doc, nested Doc, and nested TXT. A second refresh scanned five files and reported five unchanged.
2. Vertex extracted the October 24, 2026 date from the nested Google Doc. The first run produced zero verified facts because the user-entered aliases `Acme Logistics` and `delivery date` did not exactly match Gemini's output `Acme Logistics delivery` and `date`. Rerunning with those exact output aliases produced one verified fact with the source quote `Acme Logistics delivery date is October 24, 2026.`
3. Running assessment in the Reviews page produced a contradiction against the October 15, 2026 baseline, with a nine-day delta. The stored finding cites the real nested Doc at `https://docs.google.com/document/d/1dQLb0CSf6f1Fjul1s48Tc6P5W6l_mKh4IZwzz31WxMA/edit`. The page shows two alerts because an older gateway-test finding remains in this emulator project; the new finding was checked separately by its source URL.

## Remaining gap

The normal Secret Manager token store accepted the OAuth refresh token, but the test account cannot read it: `secretmanager.versions.access` returned 403. The local E2E pass used a private token file outside the repo (`/private/tmp/decision-radar-real-drive-e2e/token-store`, permissions 0700/0600) after a second OAuth grant. Steffy or a project IAM administrator needs to grant Mike's account Secret Manager Secret Accessor on the relevant secret before the normal storage path can pass. The local file store was injected only into the UAT server process; repository production code was not changed.

The alias mismatch is a UI and extraction usability finding. A reviewer must currently inspect Gemini's uncertain output and re-enter the exact entity and predicate wording before the fact becomes alert eligible.
