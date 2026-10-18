# Judge account and Connections spacing UAT

Historical password-based demo checks. The current public `/demo` flow is
documented in `PASSWORDLESS_DEMO_UAT_20261018.md`.

18 October 2026, Singapore time. Implementation commit: `3179e355`.

## Environments

- Local Next.js at `http://localhost:3035` and the updated FastAPI service at
  `http://127.0.0.1:8035`. Real Firebase email/password authentication; no auth
  or Firestore emulator. Named cloud Firestore database `decision-radar`, the
  existing Secret Manager Drive grant, actual Google Docs, Vertex Gemini,
  Cloud Tasks, and the deployed `radar-worker-dev` worker were used.
- Hosted web preview:
  `https://judge-preview---decision-radar-web-ngm5jlvo5q-as.a.run.app/judge`.
  Web revision `decision-radar-web-judge-3179e35` uses private API revision
  `decision-radar-api-staging-judge-3179e35` through the normal authenticated
  proxy. The preview revisions receive traffic through their tags. Both main
  demo URLs continue to send 100% of traffic to their PR #33 revisions.
- Workspace: `proj_e2e_rehearsal2_20261017`. Three real Google Docs contain
  deliberately synthetic Acme Logistics project data. The judge account has
  editor membership only here, with a folder-specific refresh grant. No Drive
  token was copied. The personal workspace was not modified.

## Hands-on results

| Flow | Result |
| --- | --- |
| Incorrect password, then correct password | Local UI showed an error, re-enabled sign-in, and accepted the retry. Hosted UI also signed in successfully with real Firebase Auth. |
| Refresh the configured folder | Passed in local and hosted UI. Real Drive manifest reads succeeded; unchanged inputs reused the existing completed job. The folder field was disabled; connect/disconnect controls were absent for the judge. |
| Source inventory / background work gap | Hosted and local rendered gap measured 24px. Desktop had no horizontal overflow. Saved a hosted screenshot showing both card edges. |
| Create and confirm a decision | In local UI, selected the actual original Google Doc and exact October 15, 2026 quote, created a draft, then confirmed it. |
| Extract the update | In local UI, selected the new assumption and called Gemini on the actual connected vendor update. Fresh extraction published one verified October 24, 2026 fact at `2026-10-18T01:23:36.675365+00:00`. |
| Assess | Real queued worker analysis completed with two comparisons and two alerts: the original sample decision plus the new test decision. The new alert showed the original and updated quotes and a nine-day delay. Two unrelated sample assumptions retained incomplete coverage. |
| Review | Saved Request clarification with a rationale as the judge. The UI showed Review saved and an audit entry under the judge UID. Firestore readback confirmed one retained review. |
| Archive and clean up | Archived only the new test decision in the UI. Firestore confirmed retired decision version 3 and retired assumption. Reran the assessment: one comparison and one alert remained for the original sample decisions. Original decisions and reviews were retained. |
| Access boundary | Actual authenticated requests against the local and hosted APIs returned 403 for the personal workspace, another folder, and Drive disconnect. Local API also returned 403 for synchronous refresh and starting OAuth authorization. |

Retained test history:

- Decision: `dec_70f510671d6f4d58b28ee35cbb96fefe` (retired).
- Assumption: `asm_d476bcdfc02b4939aa5e197b788ec90e` (retired).
- Alert: `alt_5901716046359f728379`; its Request clarification review remains.

Local proof artifacts are under `/private/tmp/decision-radar-judge-proof/`.
Credentials are supplied in a separate private local handoff file, never in the
PR or this repository.

## Automated and build checks

- Backend: 166 passed, 19 emulator-dependent tests skipped, 43 subtests passed.
  New checks cover explicit delegation, default editor denial, wrong folders,
  changed selected folders, generic submission, retry, viewer denial, trusted
  membership fields, and continued admin-only connection management.
- Web: 9 tests passed; lint and TypeScript passed.
- Cloud Build API: `09ca3bf8-db7f-475d-9d6d-da930139bf38`, success.
- Cloud Build web: `fcc2eafa-ccf8-4eb7-989a-563ebfa2d0d3`, success, including the
  production Next.js build and standalone server packaging check.
- Hosted proxy health: 200, API status `ok`, environment `staging`.
- Ran `graphify update .` (AST only). Generated graph changes remain local.

## Limits

The full create/confirm/extract/assess/review/archive path ran through the local
web and updated API against the actual cloud services and resulting data.
Hosted UAT repeated real sign-in, configured-folder refresh, inventory, card
spacing, and access denials. Refresh used unchanged Docs, so it reused a
completed job rather than importing a newly edited file. OAuth reconnection,
Meet monitoring, table mapping, and mobile breakpoints were outside this change.
The judge account is an application login; separately opening a Google Doc
requires that browser account's own Drive permissions. The shared sample
workspace retains edits and does not reset automatically.
