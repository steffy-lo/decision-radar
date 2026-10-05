# KAN-18 evidence viewer UAT

Tested locally on 30 September 2026 from `codex/kan18-evidence-viewer`. The branch is based on the KAN-3/4/16/17 integration commit `c03a7da`; it is not a PR against `main` yet.

## Browser checks

- Opened the live Reviews page after real Drive and Vertex extraction. The alert shows distinct original and new quotes, source titles and types, native Google Doc links, classification, and assessment coverage. The native link opened the synthetic Google Doc.
- Opened the synthetic `Needs review` scenario. Both citations show a source link and snapshot character locator.
- Clicked `Access unavailable`. The review hides the unavailable quote and source details. The fixture API response also omits the original source title, native URL, and quote.
- Clicked `Evidence unclear`. The review shows a distinct empty state while the source needed for assessment is unavailable.
- Clicked `No detected issue`. The review shows a distinct empty state for an on-time synthetic update.
- Switched back to `Access unavailable` to confirm the page refetched the selected scenario instead of retaining the previous fixture.

## Automated checks

- TypeScript typecheck and Webpack production build passed.
- Node contract tests passed (3 tests).
- Python suite passed (57 tests and 10 subtests); the extraction locator assertion passed.

## Limits

- This implements fixture-controlled unavailable-source behavior. It does not inspect each user's live Google Drive permissions.
- Old evidence without a stored locator displays `Locator unavailable for this snapshot`; new extraction records a snapshot character range.
- KAN-17 is still the integration dependency. Rebase onto merged `main`, rerun the browser flow, then open the KAN-18 PR.
- The deployed staging API still needs Firestore and Vertex runtime roles and OAuth configuration before cloud end-to-end UAT.
