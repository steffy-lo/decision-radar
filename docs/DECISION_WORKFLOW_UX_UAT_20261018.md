# Decision removal and workflow guidance UAT — 18 October 2026

## Change

The decision register now exposes the existing retirement lifecycle as **Discard draft** and **Archive decision**. Both actions require an in-page confirmation, remove the decision from the current list, and retain its record under Archived decisions. This is archival, not permanent deletion. There is no restore action in this change.

Connected workspaces now show a four-step guide: connect files, confirm a decision, extract updates, and check for conflicts. The decision form separates original evidence from the monitored deadline. Sources explains wording matching and full-date requirements; connection management is collapsed so extraction is the main task.

Reviews checks current inputs through a read-only readiness endpoint before enabling assessment. The endpoint uses the same current-fact filtering and comparison rules as assessment. Empty runs say **Nothing was assessed**, and changed inputs label the previous result as historical. Latest-run selection compares timestamps chronologically, including mixed Firestore timestamp and ISO string values.

## Environment

- Branch based on `main`; local Next.js on `localhost:3034` and changed FastAPI on `127.0.0.1:8034`.
- Chrome with Firebase Auth emulator sign-in. The test identity was granted admin membership only in `proj_workflow_ux_uat_20261018`.
- Real named Firestore database `decision-radar` in `geminimaxxing-509705`, real Vertex Gemini, and the deployed Cloud Tasks queue/private `radar-worker-dev` service.
- Two synthetic TXT snapshots were seeded in the isolated project: an October 15, 2026 baseline and an October 29, 2026 update. Their `example.com` links are test placeholders. No OAuth grant was created or copied. The user's `proj_maxxinggemini_real` project was not modified.

## Hands-on results

| Check | Result |
| --- | --- |
| Submit a draft without a quote | Passed. An exact-quote validation message appeared. |
| Create a quote-backed draft | Passed. The card said **Draft · not monitored** and explained confirmation. |
| Open Reviews with only a draft and an earlier empty run | Passed. Run assessment was disabled, **Confirm a decision first** linked to Decisions, and the earlier run said **Nothing was assessed**. |
| Cancel draft discard | Passed. The draft remained current. |
| Concurrent update during discard | Passed. A simulated version change produced HTTP 409 and preserved the draft. The client refreshed the record; retry succeeded. |
| Inspect discarded draft | Passed. It left Current decisions and appeared under Archived decisions. |
| Confirm the baseline | Passed through the real API and Firestore. Reviews then directed the user to extract facts and kept assessment disabled. |
| Extract the update with Gemini | Passed. Clicking the update's extraction control published one verified October 29 fact. |
| Run assessment | Passed through the real queue and private worker. Reviews displayed one assessed contradiction and a **14 days later** alert with both exact quotes. |
| Save a human response | Passed. Request clarification saved one review in Firestore. |
| Archive an active decision | Passed. The real API retired the decision and its assumptions. Readback confirmed both UAT decisions and assumptions retired, two revisions retained, and one review retained. |
| Mobile Reviews at 390 × 844 | Passed. Navigation, guide, and controls rendered with content width equal to viewport width; no horizontal overflow. The temporary viewport override was reset. |

## Automated validation

- Backend: 163 passed, 19 skipped, 43 subtests passed. Skips require additional emulator/integration setup. The missing test runner and declared spreadsheet dependency were installed only into a temporary test folder.
- Web lint, TypeScript check, nine server/domain tests, and the webpack production build passed.
- Regression coverage includes no-comparison messaging, incomplete coverage, assessment readiness, mixed timestamp ordering, retained draft evidence, replay, stale versions, and viewer rejection.
- CodeRabbit was not run: automatic approval review rejected external source-code transmission. Local review and tests were completed instead.
- `graphify update .` refreshed the isolated worktree's code graph without an LLM call.

## Release limits

The changed UI was tested locally against real persistence, extraction, and task delivery. The source snapshots were seeded; this pass did not repeat Google OAuth, a fresh Drive import, Meet delivery, or table ingestion. Deploy the API with `/assessments/readiness` before the web change, then repeat the connected flow and failure/retry checks on the deployed revisions before merging. Keep the PR open until that integrated check is complete.
