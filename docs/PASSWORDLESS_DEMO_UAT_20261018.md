# Passwordless connected demo UAT

18 October 2026, Singapore time. Implementation commit `74c2642f`.
This supersedes the password-based entry checks in the earlier judge UAT.
The owner explicitly approved public sample-workspace mutation access, one-hour
sessions and admission limits in chat before implementation.

## Environment and results

Hosted web revision `decision-radar-web-demo-74c2642`, private API revision
`decision-radar-api-staging-demo-74c2642`, project `geminimaxxing-509705`, region
`asia-southeast1`. Browser UAT used the `/demo` page on the hosted preview with
real Firebase Anonymous Auth, named cloud Firestore, the existing OAuth grant,
actual Google Docs, Vertex Gemini, Cloud Tasks and `radar-worker-dev`.

| Check | Result |
| --- | --- |
| Demo entry | Passed. Demo email is prefilled with `demo@decision-radar.example`; one Try demo button; no password input or Google option. One click created a separate visitor session and opened Connections. |
| Refresh | Passed through the real Drive manifest path. Three sources appeared. Unchanged files reused the existing completed refresh job. Folder field was locked and connection management controls absent. |
| Sources spacing | Passed. Measured 24px between the last connected-source card and Background work, with no desktop horizontal overflow. Screenshot inspected. |
| Create and confirm | Passed using the original connected Doc, exact October 15, 2026 quote, entity `vendor_acme` and predicate `delivery_date`. |
| Fresh Gemini extraction | Passed. One verified October 24 fact published at `2026-10-18T01:53:33.510342+00:00` for the new assumption. |
| Assessment | Passed through the actual queued worker. Two comparisons and two alerts, including the new nine-day conflict; unrelated sample assumptions retained incomplete coverage. |
| Review | Passed. Saved Request clarification with rationale. UI and Firestore retained the review under the individual visitor UID. |
| Archive / cleanup | Passed. Only the test decision and assumption were retired; decision version 3. Reran the assessment and confirmed one comparison and one original alert remained. |
| Expiry and recovery | Passed. Expired only the disposable visitor membership in Firestore. The running Sources view could no longer load protected data. Sign out returned to passwordless entry; Try demo created a fresh session and restored the three connected sources. |
| API boundaries | Real authenticated calls returned 401 without a token, 422 for client-selected project/role fields, and 403 for personal workspace, another folder, Drive disconnect and expired membership. Repeated admission returned the same expiry. |

Retained test history: decision `dec_6dd1b8d8ab014d28acdc7a7fdf7de9aa`, assumption
`asm_f74bcf504cb045e8b5714e71423acd13` (both retired), alert
`alt_7d238d54694a0bfd8c3a` and its saved review. Browser test visitor
`qHZ8tiM2KISVXostZcWkyws6X7l1` was deliberately expired. Original sample decisions
and reviews were preserved. Personal workspace data was not modified.

Proof artifacts: `/private/tmp/decision-radar-demo-proof/` and the API boundary
proof `/private/tmp/decision-radar-demo-security-proof.json`.

## Validation

173 backend tests passed; 19 emulator-dependent tests skipped; 43 subtests
passed. Nine web tests, lint and TypeScript passed. Session tests cover fixed
scope, one-hour expiry, idempotent retry, changed folders, existing memberships,
authentication, spoofed request fields, ten-new-sessions-per-minute admission
and retry after the window changes. Ran `graphify update .` (AST only).

API build `698e67c2-77d7-4ef4-8f43-1b90137b8cc2` and web build
`fe853204-9fd5-4a49-8d99-a14fbca68872` passed, including production standalone web
packaging. Both images were built from `74c2642f`; subsequent documentation-only
commits do not change runtime source.

## Limits

Documents contain sample content but use real connected services. Refresh did
not import a newly edited file. The one-hour boundary was tested by expiring a
disposable membership, not by waiting an hour; backend tests cover fixed
identity-age expiry. Rate-limit behavior was tested with the transactional fake;
normal admission and retry used actual Firestore. Mobile breakpoints, Meet and
OAuth reconnection were outside this change. The shared sample workspace keeps
changes between visits. Google Doc links still require the browser's own Drive
permissions. Main-host rollout and its final checks are recorded in the PR.
