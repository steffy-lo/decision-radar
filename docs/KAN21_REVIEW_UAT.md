# KAN-21 review workflow UAT

3 October 2026. Tested the live Reviews page at `/projects/proj_kan21_uat/reviews` in Chrome with synthetic vendor-delay data, a Firebase Auth emulator account, and a disposable in-memory FastAPI server using the real review routes. This pass did not exercise Firestore or a real Google Drive connection.

- Keep decision: selected the action, entered a rationale, clicked Submit review, and saw “Review saved” with an audit entry showing the actor and unchanged revision 1.
- Revise decision: reset the synthetic data, changed the statement to “Launch on October 27, 2026”, entered a rationale, clicked Submit review, and saw revision 2 with before/after statements in the audit entry.
- The Reviews page displayed the original and new evidence quotes, source links, finding classification, and coverage before each action.
- Automated API tests cover Dismiss, Retire, Request clarification, idempotent retry, stale revision conflict, and viewer rejection. These paths were not separately clicked in this browser pass.
- The assessment results endpoint now hides an incomplete publishing run and its records until publication completes; a regression test covers a newer publishing run alongside a prior completed run.

The fixture-only demo view does not call the review API. A project with a completed live assessment is required to use these controls. Recheck with Firestore and real project membership after the upstream KAN-4, KAN-16, KAN-17, and KAN-18 changes land.
