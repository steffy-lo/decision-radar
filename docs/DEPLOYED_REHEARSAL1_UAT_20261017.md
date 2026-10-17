# Deployed staging rehearsal 1 UAT, 17 October 2026

Environment: public web `decision-radar-web-00012-ct9`, private API `decision-radar-api-staging-00014-42c`, private worker `radar-worker-dev-00013-ng2` (all from PR #27 head `0a2c587`), named Firestore `decision-radar`, Cloud Tasks `radar-jobs` (3 attempts, 10–300 s backoff). Signed in as the approved UAT account. Clicks by Claude Code in the in-app browser; Google sign-in and OAuth consent by Mike. All content synthetic.

| Step | Evidence | Result |
| --- | --- | --- |
| Provisioning | New project `proj_e2e_rehearsal1_20261017` (Firestore project doc + admin membership). `scripts/bootstrap-project-secrets.sh` created drive/meet secrets with secret-level API and worker roles, 0 versions. | PASS |
| Health/IAM | `check-staging-health.sh`: web 200, proxy 200, direct API 403, direct worker 403. | PASS |
| Drive connect | OAuth returned to the app, connection `active`; Drive secret gained 1 enabled version (metadata only inspected). No `storage_unavailable`. | PASS |
| Fresh refresh | Job `task-3171d4a5…` completed, attempt 1. 11 sources: Doc, TXT, subfolder Doc and TXT, Meet-transcript Doc, three tables (`mapping_required`). | PASS |
| Unchanged refresh | Second click reused the completed receipt: still 1 refresh job, 11 sources. | PASS |
| Decision | Draft from `Decision record - synthetic launch` exact quote; confirmed active r1 (`dec_5cbc2264…`). Two synthetic downstream decisions created and confirmed in the UI (`dec_a6d86a7c…`, `dec_e027ed2a…`). Dependencies `dep_bc1fefe5…` (enables) and `dep_38652b3f…` (requires_review_of) created through `POST /dependencies` from the signed-in session (no UI exists). | PASS (dependency entry is API-only) |
| Gemini extraction | `vendor-update.txt` → 1 verified fact, “Acme Logistics delivery date is October 24, 2026.”, first attempt. Subfolder Doc `Nested vendor note` → same verified fact; an unrelated “October 15 target” phrase left `uncertain`. | PASS |
| Assessment | Job `task-20de1f96…` completed attempt 1 (~25 s). Run `run_2f0afa3927074cdf911e`: 2 findings, 2 alerts (one per source), medium, +9 days, exact quote spans for baseline and update; two downstream assumptions “evidence unclear”. | PASS (see finding 1) |
| Impact graph | Trigger → challenged launch → onboarding → announcement. Enter on a focused downstream node opened its detail: 4-step ordered path, “projected impact … no separate contradiction evidence”. | PASS |
| Human review | `alt_4c2c2b65…` Request clarification (`review_fa899482…`); `alt_ec2bb2d9…` Keep (`review_d6935477…`). Decision stayed r1. Audit entry visible after reload. | PASS (see findings 2, 3) |
| Brief | `brief_3f90525c8de6551f8bfa64ac` from the kept alert: decision, severity, review rationale, baseline/update quotes with Drive links, both affected paths. | PASS (see finding 4) |
| Docs export | Consent cancelled once, then approved; export completed attempt 1. Private Doc `1xUK8I2kd5ubZcdml4rIn7EQ-HLFg8ohrcHeVkzioMU0` opened and matched the brief. | PASS |
| Export recovery | Export row set to `failed` with `documentId`/`nativeUrl` cleared (simulated post-create timeout). UI: “The export failed. Retry will look for the same document.” Retry export → `completed`, same document ID, attempts 1→2. Drive was not listed to prove no second Doc. | PASS (controlled failure, not a real Google outage) |
| Bad folder | Unavailable folder ID → API 400, message “The selected Drive folder or file is unavailable. Reconnect or check access.”, no job, no stale Completed. Valid folder restored → completed, 11 sources. | PASS |
| Worker failure | Added synthetic Doc `retry-drill-20261017 (synthetic)`. First attempt with worker secret access removed still completed (IAM change not yet effective; new Doc became source 12 with no duplicates). After ~9 min and a Doc edit, job `task-c9cbb454…` failed attempts 1–3 (`handler_failed`) then `failed`/`delivery_exhausted`; UI showed “Delivery stopped before this work completed. You can retry it.” Connection stayed `active`; 12 sources, no partial records. Access restored by Mike; after ~5 min, **Retry work** clicked in the UI → same job, generation 2, completed on its first attempt. The edited drill Doc gained a second immutable version (`ver_5cd9d810…`); 12 sources, 4 job records, no duplicates; connection `active`. | PASS |

## Findings
1. One contradicting claim present in two source files produces two alerts for the same decision; reads as a duplicate in a demo.
2. Briefs page only counts closing reviews (keep/revise/retire/dismiss) but says “Review an alert from this assessment” when a clarification review exists.
3. Review audit history does not refresh after Submit; needs a reload. It shows the raw Firebase UID instead of a name.
4. Dependencies have no UI; downstream impact setup needs the API.
5. Secret Manager IAM removal took several minutes to apply; recovery drills must wait for propagation.

## Limits
Single rehearsal (KAN-25/26 need two consecutive). Downstream decisions and dependencies are synthetic and API-entered. Export failure was a controlled Firestore state, not a Google API outage. Meet intake, table mapping and KAN-11 native ACL filtering were not exercised.
