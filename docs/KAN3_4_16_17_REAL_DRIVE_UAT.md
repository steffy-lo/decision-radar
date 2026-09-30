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
- The integrated branch passes web lint, a Next.js webpack production build, and 57 Python tests (38 core and 19 radar service tests). Turbopack cannot follow this worktree's external `node_modules` symlink during a build.
- The Sources page was opened and clicked through in the browser. The synthetic emulator project shows the Drive connection control, monitored assumption, alias inputs, and source library.
- The Drive folder and nested folder were listed through the connected Drive account. The native Docs were read back and contain the expected baseline and October 24 vendor update text.

## Live browser pass

`umalimike36@gmail.com` was confirmed on the OAuth test-user list. The user reviewed Google's test-app warning and completed Drive read-only consent. The app returned to Sources with an active connection.

1. Folder refresh scanned five files and created five sources: root Doc, root TXT, saved Meet-style transcript Doc, nested Doc, and nested TXT. A second refresh scanned five files and reported five unchanged.
2. Vertex extracted the October 24, 2026 date from the nested Google Doc. The first run produced zero verified facts because the user-entered aliases `Acme Logistics` and `delivery date` did not exactly match Gemini's output `Acme Logistics delivery` and `date`. Rerunning with those exact output aliases produced one verified fact with the source quote `Acme Logistics delivery date is October 24, 2026.`
3. Running assessment in the Reviews page produced a contradiction against the October 15, 2026 baseline, with a nine-day delta. The stored finding cites the real nested Doc at `https://docs.google.com/document/d/1dQLb0CSf6f1Fjul1s48Tc6P5W6l_mKh4IZwzz31WxMA/edit`. The page shows two alerts because an older gateway-test finding remains in this emulator project; the new finding was checked separately by its source URL.

## Secret Manager access and normal-store pass

The first run's normal Secret Manager token store accepted the OAuth refresh token, but Mike's account could not read it: `secretmanager.versions.access` returned 403. A temporary local pass used a private token file outside the repo (`/private/tmp/decision-radar-real-drive-e2e/token-store`, permissions 0700/0600). This injection was only in the UAT server process; repository production code was not changed.

After Secret Manager Secret Accessor access was granted, direct access to the existing secret succeeded and its stored refresh token returned HTTP 200 from Google's token endpoint. The API was restarted without the local token-store injection. The disposable Firestore emulator connection was pointed back to the existing Secret Manager secret, so no new Google consent was needed. In the browser, folder refresh scanned five real Drive files and reported five unchanged; live Vertex extraction produced one verified fact from the nested Doc; review assessment still showed the nine-day contradiction. This completes the local end-to-end pass through the repository's normal Secret Manager adapter.

## Alias follow-up

The first live run exposed a word-boundary mismatch: Gemini used `Acme Logistics delivery` / `date` while the reviewer entered `Acme Logistics` / `delivery date`. A later run reversed that split, even with temperature set to zero. The extraction validator now accepts either split only when the combined phrase is identical to one unambiguous trusted entity/predicate alias pair and appears in the verified source quote. Unrelated or ambiguous candidates stay uncertain. The Sources page also lets a reviewer copy the candidate's entity or predicate wording into each field separately after checking it against the selected assumption.

The revised flow was clicked through in the browser on the nested Google Doc. An unresolved run showed zero ready facts and the two wording controls. Using the displayed wording alone still produced zero on the next call because Gemini changed the split. After the backend fix, another live Vertex run returned the other split and published one verified fact. The Reviews page was opened and assessment rerun; it continued to show the nine-day contradiction. This fixes the observed mismatch while retaining manual review for paraphrases and unrelated candidates.

The deployed runtime identity has not been tested. Before deployment, check which service account runs the API and grant it access only to the required Secret Manager secret. The current browser result uses Firebase emulators for project state, a local Next.js/API server, real Drive, real Secret Manager, and real Vertex AI.
