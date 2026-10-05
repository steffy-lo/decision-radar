# KAN-18 and KAN-21 integration check

5 October 2026. Integrated the evidence viewer and review workflow with the merged KAN-17 assessment path on `codex/kan18-21-integration`.

## Verified

- Python suites: 54 core tests and 21 service tests passed before the final source-status regression; that regression was then run with the core suite. The live Firestore emulator passed two KAN-17 transaction tests and two KAN-21 review tests, including idempotent Keep, Revise, and audit-history readback.
- Web lint and Webpack production build passed. The default Turbopack build could not bind its worker port in the local sandbox; Webpack completed the same TypeScript and production compilation checks.
- In Chrome, signed in with the existing Firebase Auth emulator tester, opened the integrated Sources page, checked that the two source cards appear once, opened Reviews, saw the original and updated quote cards and coverage, entered a rationale, clicked **Submit review**, and saw **Review saved** plus one audit-history entry with unchanged revision 1.
- Visual check showed the evidence cards, review state, and audit history in the expected layout.

## Scope of this pass

The browser pass used synthetic vendor-delay data and a disposable in-memory API to exercise the merged web code and review route. Separate integration tests used real Firestore emulator transactions. This pass did not repeat the earlier real Drive and Vertex run after the merge, and does not establish deployed cloud readiness. The fixture's older evidence has no stored locator, so the UI correctly says the locator is unavailable; new extraction records the snapshot character range.
