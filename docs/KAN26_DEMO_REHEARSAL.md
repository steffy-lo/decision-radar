# KAN-26 demo rehearsal

Prepared 5 October 2026 from the [MVP scope](https://geminimaxxing.atlassian.net/wiki/spaces/GeminiMaxx/pages/163960/MVP+Scope+Delivery+Plan+Backlog) and the vendor-delay fixture. Run the full rehearsal after KAN-8 and KAN-9/19 are merged. Record two consecutive complete runs before marking KAN-26 done.

## Demo path

Use a fresh project folder or the deterministic vendor-delay fixture. Keep the original PRD delivery date of 10 October 2026 and the updated vendor note date of 24 October 2026. The confirmed launch decision is 20 October 2026.

1. **Sources:** Sign in, select the project, connect one Drive folder, and run manual refresh. Check that the PRD, vendor note, and any transcript Doc or TXT appear once with source links and healthy status. Repeat refresh and confirm no duplicate sources or jobs.
2. **Decisions:** Open the decision register. Show the launch decision, owner, revision, preserved rationale, and its monitored delivery-date assumption. Confirm that source wording and the trusted entity/predicate mapping are clear.
3. **Reviews:** Run assessment. Show the original quote beside the new vendor quote, the date conflict, assessed coverage, and the link to each source. Explain that the fact directly challenges the launch decision.
4. **Impact graph:** Open the challenged alert's graph. Select the launch decision and each downstream effect by mouse and keyboard. Show the ordered dependency path and point out which nodes have direct evidence and which are projected effects. Test pan and zoom, then repeat at a narrow viewport.
5. **Human review:** Save Keep or Revise with a rationale. Confirm that the saved outcome and audit history appear once, and that no decision changes without a human action.
6. **Failure and fallback:** Check empty, permission/error, and incomplete-coverage states. If live Drive or Vertex is unavailable, reset to the vendor-delay fixture and repeat the same narrative without claiming it is a live run.

The MVP scope explicitly excludes Google Docs export and durable briefs. The current Briefs page is an empty state. Do not present a brief export as part of this rehearsal despite the older KAN-26 ticket wording.

## Pass record

| Run | Environment | Source and decision | Alert and graph | Review and recovery | Result |
| --- | --- | --- | --- | --- | --- |
| Preflight, 5 Oct | Local app with synthetic API | Sources showed two files once; Decisions showed three records and the quote-backed draft form | Review showed one cited alert and assessed coverage; graph remains on draft PR #13 | A saved Keep review and one audit entry were visible; job retry was checked separately on draft PR #12 | Partial: full path waits for draft PRs |
| Rehearsal 1 | Pending | Pending | Pending | Pending | Pending |
| Rehearsal 2 | Pending | Pending | Pending | Pending | Pending |

## Open dependencies

- KAN-8 draft PR #12 now merges cleanly with main, but its production refresh/analysis worker handlers still need wiring and delivery testing.
- KAN-9/19 draft PR #13 now merges cleanly with main. The synthetic graph was clicked through, including downstream node selection; it still needs the integrated end-to-end pass after Steffy's wiring.
- The preflight above used a controlled local API. It does not establish a fresh cloud Drive, Vertex, Firestore, and Cloud Tasks end-to-end pass.
- Before a final demo, verify keyboard focus, narrow-screen layout, source recovery, and the two full repeat runs.

Reset the fixture by starting from `fixtures/vendor-delay.json` and using a fresh project ID or clean emulator data. Do not reuse the synthetic review project after it has an audit entry when demonstrating a new review.
