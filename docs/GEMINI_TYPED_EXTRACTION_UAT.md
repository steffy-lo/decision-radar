# Gemini typed extraction fix — 18 October 2026

## Problem and change

The Sources button could return `candidate has an invalid typed value` after Gemini produced structurally valid JSON containing an invalid date, amount, or empty text value. The original response schema declared every value as an unconstrained string, so the failure surfaced only during conversion into a published fact. Any invalid candidate rejected the entire response. The failed historical model payload was not retained, so its exact value cannot be recovered.

The response schema now uses separate date, decimal, and enum variants for both facts and decision assumptions. Dates carry the Vertex-supported `date` format, decimal amounts must be finite and include a unit, and enum values must be nonempty. Older date/enum candidates containing `unit: null` remain accepted locally. Gemini gets one corrective retry for invalid JSON or schema values. Persistent failure returns field paths and format guidance; logs omit candidate values and source text. Quotes and source visibility checks still gate publication.

Gemini now receives the trusted entity and predicate labels supplied for this extraction. It is instructed to use those labels only when the source supports the same subject and attribute. This addresses the user's accompanying Acme Logistics/name-boundary mismatch without loosening deterministic entity or quote validation.

## Automated and real-service checks

- Representative reproduction: a candidate date `October 29, 2026` passed the former raw schema and failed later with the reported error. The regression test failed before the change and passes afterward.
- Full backend suite: 184 passed, 19 emulator-only tests skipped, plus 52 subtests on current main. Cloud Tasks environment values were cleared for the test process so the test expecting missing cloud configuration did not inherit this machine's live local settings. No emulator was started.
- New cases cover invalid calendar dates, natural-language dates, nonnumeric/nonfinite amounts, missing units, empty enum values, legacy null units, malformed JSON correction, bounded retry exhaustion, field diagnostics, and an HTTP failure that leaves all previously saved data unchanged.
- Real Vertex Gemini 2.5 Flash, `us-central1`, project `geminimaxxing-509705`: the update text “Delay recorded, Acme Logistics vendor delivery date changed to October 29, 2026 instead” returned one quote-validated, ready fact with date `2026-10-29` and the requested Acme Logistics/delivery date labels. Two matching-date calls passed.
- Real Gemini negative cases: an October 29 update without a year produced zero eligible facts; an update about Beta Freight with Acme Logistics as the target also produced zero eligible facts.
- CodeRabbit raised one minor issue in diagnostic field filtering. It was corrected and covered by a regression test. A final fresh CodeRabbit review completed with zero issues.
- `graphify update .` completed with AST-only extraction and refreshed the existing graph. Existing unrelated working changes were preserved.

## Deployment and browser UAT

API build: `f7001510-1147-4c89-aeeb-367ceef00c7f`.
Image digest: `sha256:c4a02ed09b4a40d6a81fac503b2bce6568a3650f3f1d6f910242cd3d4eb2f4a0`.
Target service: `decision-radar-api-staging`, `asia-southeast1`.
Previous serving revision: `decision-radar-api-staging-login-50884fe`.
Candidate revision: `decision-radar-api-staging-typed-fix-main-20261018`.

The first candidate was based on the original chat checkout, which preceded the deployed API. Extraction succeeded in the signed-in workspace and persisted one confirmed `2026-10-29` delivery fact. A repeat click preserved the fact. Reviews then returned HTTP 404 for its readiness endpoint. Staging traffic was restored immediately to `decision-radar-api-staging-login-50884fe`; clicking Try loading again recovered Reviews and showed one comparable assumption. The saved fact survived rollback.

The final fix is based on `origin/main` at `0cccf94`, whose backend is identical to the prior serving revision's `50884fe` backend. The existing dirty chat checkout was restored to its prior branch, and only the five fix/test files were transferred to the dedicated worktree. The final candidate returned HTTP 200 for health and preserved all 43 existing OpenAPI paths and their methods, including the readiness endpoint. It was then promoted to 100% of staging API traffic. Final browser UAT passed in the existing signed-in Chrome workspace:

- Selected the active Vendor delivers by launch deadline requirement and the October 29 update Doc. Changed the predicate wording to `delivery_date` to force a fresh model call instead of cached reuse, then repeated with the original `delivery date` wording. Both returned HTTP 200 on the final revision (about nine seconds each) and showed Facts saved with one verified fact ready to compare.
- Firestore held exactly one published fact for this extraction: `fact_4e9eeaf3b18ea61381a4`, entity `vendor_acme`, predicate `delivery_date`, value `{type: date, value: 2026-10-29}`, modality confirmed. The saved alias fields were restored to Acme Logistics and delivery date.
- Opened Reviews. Readiness loaded normally and showed one active decision, one monitored assumption, and one ready to compare. Clicked Run assessment. The real Cloud Tasks/worker job `task-d6b689d84ec20adeaec8c337615a5a1ea16d499f57fdc12f87b14d53dead7f8b` completed on its first attempt.
- The rendered page showed Decisions need review, one comparison, one alert, zero assumptions with incomplete coverage, and Date moved past the target — 14 days later. The original October 15 quote and new October 29, 2026 quote were both visible with snapshot locators and Google Doc links.
- The saved completed run references finding `fnd_b17d8a66a4cc11b23d62` and alert `alt_4a266d53d1f9398a638a`. No human review was submitted; the decision remains unchanged and the alert is open.
- Visually inspected the final page and captured extraction and assessment screenshots as chat artifacts. No clipping or missing result content was observed in the tested desktop view.

The generated graph files were refreshed locally and left outside the focused code/documentation commit. No feature PR was merged during this work.

## Limits

A malformed output from the live model cannot be forced reliably, so automatic retry and persistent schema failure are tested with controlled model responses through the actual adapter and HTTP route. Missing-year and wrong-subject rejection were exercised against real Gemini. The broader Doc/TXT/nested Doc/Meet ingestion matrix is outside this extraction-only patch; its existing checks were not rerun. No decision review or confirmation is performed as part of this fix.
