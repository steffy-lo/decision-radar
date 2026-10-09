# KAN-26 demo rehearsal

Prepared 5 October 2026 from the [MVP scope](https://geminimaxxing.atlassian.net/wiki/spaces/GeminiMaxx/pages/163960/MVP+Scope+Delivery+Plan+Backlog) and the vendor-delay fixture. KAN-9/19 merged on 6 October and KAN-8 merged on 8 October. Record two consecutive complete runs before marking KAN-26 done.

## Demo path

Use a fresh project folder or the deterministic vendor-delay fixture. Keep the original PRD delivery date of 10 October 2026 and the updated vendor note date of 24 October 2026. The confirmed launch decision is 20 October 2026.

1. **Sources:** Sign in, select the project, connect one Drive folder, and run manual refresh. Check that the PRD, vendor note, and any transcript Doc or TXT appear once with source links and healthy status. Repeat refresh and confirm no duplicate sources or jobs.
2. **Decisions:** Open the decision register. Show the launch decision, owner, revision, preserved rationale, and its monitored delivery-date assumption. Confirm that source wording and the trusted entity/predicate mapping are clear.
3. **Reviews:** Run assessment. Show the original quote beside the new vendor quote, the date conflict, assessed coverage, and the link to each source. Explain that the fact directly challenges the launch decision.
4. **Impact graph:** Open the challenged alert's graph. Select the launch decision and each downstream effect by mouse and keyboard. Show the ordered dependency path and point out which nodes have direct evidence and which are projected effects. Test pan and zoom, then repeat at a narrow viewport.
5. **Human review:** Save Keep or Revise with a rationale. Confirm that the saved outcome and audit history appear once, and that no decision changes without a human action.
6. **Failure and fallback:** Check empty, permission/error, and incomplete-coverage states. If live Drive or Vertex is unavailable, reset to the vendor-delay fixture and repeat the same narrative without claiming it is a live run.

The MVP scope explicitly excludes Google Docs export and durable briefs. The current Briefs page is an empty state. Do not present a brief export as part of this rehearsal despite the older KAN-26 ticket wording.

## Demo script and reset

Use the live synthetic project only for a read-through of an already reviewed
alert. For the acceptance rehearsal, start a clean review project so the human
action and its audit entry are new. Do not clear the existing synthetic audit
history to make it look fresh.

1. Open **Decisions** and name the confirmed launch decision, its owner, and
   the expected Acme delivery date. Explain that the decision stays unchanged
   until a person reviews the alert.
2. Open **Sources**. Show the active Drive folder, the Doc/TXT/transcript and
   nested Doc inventory, and the source links. Refresh once and check that the
   count does not grow for unchanged files. Use the trusted Acme Logistics and
   delivery-date wording for the vendor TXT. A repeat extraction of the same
   verified snapshot should retain its fact after PR #20.
3. Open **Reviews**, run assessment, and read the original 15 October quote
   beside the confirmed 24 October quote. State that the nine-day difference
   directly challenges the launch decision; the two other assumptions have
   unclear coverage rather than a confirmed contradiction.
4. Open the impact graph. Select the direct challenge, then both downstream
   decisions. Explain that the latter are projected effects through recorded
   dependencies, with the trigger evidence linked separately. Check Enter or
   Space on a focused node and Fit View at phone width.
5. On a fresh alert, save a human review with a short rationale. Check one new
   audit entry and confirm the decision revision changes only if the chosen
   action explicitly revises it. This step is still required for rehearsal 2.
6. For recovery, use an unavailable folder ID and show its access message,
   then restore the valid folder and confirm the source count. If live Drive
   or Vertex is unavailable, open the **Demo workspace** from the home page.
   Its synthetic review links show access-unavailable, evidence-unclear, and
   no-issue states. Say clearly that fixture mode does not save review actions.

The current live UAT folder is `1uc4D6a_jXKJxfJOq1gecBeCDmPtN8W9a` under
project `proj_oauth_pr10_uat_20261007`. It contains seven synthetic files as
of 9 October. A clean rehearsal project needs its own Drive connection or a
documented fixture seed; do not copy a refresh token between projects. If a
new project cannot be set up, record the review step as untested rather than
counting the read-through as rehearsal 2.

## Pass record

| Run | Environment | Source and decision | Alert and graph | Review and recovery | Result |
| --- | --- | --- | --- | --- | --- |
| Preflight, 5 Oct | Local app with synthetic API | Sources showed two files once; Decisions showed three records and the quote-backed draft form | Review showed one cited alert and assessed coverage; graph was on draft PR #13 during this check and merged the next day | A saved Keep review and one audit entry were visible; job retry was checked separately on draft PR #12 | Partial: full path waits for KAN-8 |
| Graph integration, 6 Oct | Merged app on localhost:3012, merged API on 127.0.0.1:8012, Firebase Auth and Firestore emulators | Signed in through Firebase Auth emulator to the project from the earlier real Drive and Vertex run. The saved nested Google Doc fact moved the delivery date from 15 to 24 October. Added two synthetic downstream decisions and dependencies in the emulator through the normal impact store. | Clicked Run assessment twice. Both runs showed two findings, two alerts, and assessed coverage with stable alert IDs. Opened the new nested-Doc alert graph and clicked the final downstream node; the four-step ordered path and dependency rationales appeared, with direct evidence restricted to the trigger. | Saved Request clarification on the nested-Doc alert and verified one audit entry with the rationale and unchanged decision revision. Job delivery, fresh Drive refresh, and a new Vertex extraction were not part of this pass. | Graph, assessment, and review API/UI path passed after PR #13 merged. This is not a complete KAN-26 rehearsal. |
| Rehearsal 1, 8 Oct | Local web on localhost:3020, API on 127.0.0.1:8020, Firebase Auth emulator, named cloud Firestore, real Drive and Vertex, private Cloud Tasks worker | After KAN-8 merged, Sources showed the active Drive connection and five Doc/TXT/Meet/nested snapshots. Refresh returned a completed receipt and reused the existing completed job. Three quote-backed decisions were active. | Added two synthetic dependencies through the normal graph store before the walkthrough. The graph showed one direct challenge, two downstream effects, and a four-step ordered path. Mouse and keyboard selection worked; the graph remained usable at 390px width. | A fresh Gemini extraction of the same vendor TXT first returned a different entity/predicate interpretation and zero verified facts. The real worker assessment completed with zero alerts and three unclear assumptions. The built-in retry extracted one verified fact; a second real worker assessment restored one cited alert with two unrelated assumptions marked unclear. Saved Keep decision with a rationale; the audit history had one Keep and the earlier Request clarification, with decision revision unchanged. | Completed with the supported retry. The extraction variability is a KAN-23 case. One more consecutive complete rehearsal is needed before KAN-26 can pass. |
| Deployed stability pass, 9 Oct | Public Cloud Run web, private API revision `00006-n6b`, real Drive folder, named Firestore, Cloud Tasks worker, signed-in browser | The seven-file Drive folder refreshed without duplicates. A repeated vendor extraction reused the prior verified October 24 fact after PR #20's fix; the saved extraction timestamp stayed unchanged. Three active decisions remained visible. | Assessment completed with one cited nine-day alert and two assumptions with unclear coverage. The graph showed a direct challenge, two downstream decisions, and the ordered path. Mouse and keyboard selection worked; Fit View worked at 390px. | Unavailable-folder error and recovery passed. Fixture access-unavailable, evidence-unclear, and no-issue states displayed clear copy. The live alert already had saved reviews, while fixture mode has no review control, so this pass could not save a new human review. | Partial. It verifies the deployed stability fix and supporting paths, but it is not rehearsal 2. |
| Rehearsal 2 setup, 9 Oct | Public Cloud Run web, private API, isolated synthetic project `proj_kan26_rehearsal2_20261009` | Project and Mike's Firebase admin membership created; the deployed Sources page loaded with no files | Pending | Google Drive consent reached the app, but the callback returned `storage_unavailable` because the new project has no token secret or scoped API service-account grants yet. No review action was attempted. | Incomplete. Do not count this as the second rehearsal. |

## Open dependencies

- KAN-8 PR #12 is merged. Its real Drive, Secret Manager, Cloud Tasks, Cloud Run worker, named Firestore, and Vertex path passed in its own UAT. The 8 October rehearsal above used a completed refresh receipt and did not create a fresh Drive job.
- PR #20 merged the same-snapshot verified-extraction reuse rule and passed its deployed browser check. KAN-23 still needs the broader measured quality gate and changed-evidence evaluation. Keep unclear coverage visible; do not treat an earlier saved alert as the current assessment result.
- Before a final demo, run a second consecutive complete browser walkthrough on a clean review project so a new human action and audit entry can be verified. Production sign-in and the deployed web/API path passed on 9 October; the remaining run needs a fresh review, keyboard and narrow-screen checks, and relevant failure/retry states.
- The isolated second-run project is ready, but its Drive callback needs a new Secret Manager secret and narrowly scoped API service-account roles. The requested IAM change is awaiting explicit approval; the prior test project's token was not copied. After access is set, reconnect Drive in the isolated project and complete the full path above.

Reset the fixture by starting from `fixtures/vendor-delay.json` and using a fresh project ID or clean emulator data. Do not reuse the synthetic review project after it has an audit entry when demonstrating a new review.
