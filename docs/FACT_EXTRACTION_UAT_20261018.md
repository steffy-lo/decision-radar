# Guided fact extraction UAT — October 18, 2026

## Environment

Hosted Cloud Run web preview `sources-preview`, connected to the existing private
`decision-radar-api-staging` service, real Gemini extraction, Firestore and the
configured Drive connection. Workspace: `proj_e2e_rehearsal2_20261017`.
The Google Docs contain deliberately synthetic sample commitments; these checks
use the live connected services rather than fixture API responses.

## Hands-on checks

- Entered through `/demo` using a fresh passwordless visitor session.
- Sources has one extraction action for the selected document. The extraction
  card has no numbered badge or internal entity/predicate identifiers.
- The form starts with explicit selections. Its disabled explanation advances
  from requirement, to update document, to name, to information description.
  Completing the fields enables the single action.
- Opened question-mark help and closed it with Escape. Labels remain separate
  from help buttons. Required instructions remain visible outside tooltips.
- Opened the saved copy of **Acme Logistics vendor update** inside the app and
  read the actual stored Drive text, including the full October 24, 2026 date.
- Selected the original October 15 delivery requirement and deliberately entered
  **Unrelated supplier** and **invoice status**. Real Gemini returned an unclear
  match, published zero facts, and the UI explained how to correct the name.
- Corrected the phrases to **Acme Logistics** and **delivery date**, then retried.
  Real extraction published one verified fact with its supporting quote. The
  result identified the requirement actually checked and linked to next steps.
- Opened Reviews and ran the real assessment. It completed with one comparison,
  one alert and the expected nine-day delay. The other two unrelated requirements
  retained incomplete coverage. Existing review history was preserved.

## Automated checks and limits

Lint, TypeScript and all 12 web tests passed, including missing-input ordering,
viewer/missing access, paused/unready documents, in-progress extraction, and
plain-language guidance for unresolved or uncertain evidence.

No personal workspace data or Drive documents were edited. No new decision or
review was needed: the sample workspace already has an active baseline decision.
The successful retry restored its verified vendor fact after the mismatch test.
A deliberate Gemini service outage, viewer browser account and paused-source
mutation were not exercised in hosted UAT; their readiness states have focused
logic coverage. Spreadsheet ingestion is unchanged and was not retested.

Final preview verification and release status are recorded in PR #35.
