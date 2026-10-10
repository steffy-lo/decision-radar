# KAN-5 source version and citation check

## Storage and API

Set `SOURCE_SNAPSHOT_BUCKET=decision-radar-source-snapshots-geminimaxxing-509705` on the API and worker in staging. The bucket is in `asia-southeast1` with uniform access and public access prevention. The shared staging API/worker service account has object creation and read access; it has no object deletion role on this bucket. The bucket removed its default project-viewer reader bindings.

Refresh writes the normalised text once to a content-addressed Cloud Storage object and creates `projects/{projectId}/sources/{sourceId}/versions/{versionId}` in Firestore. The current source document points at that version while retaining the current text for the existing UI. An edited Doc gets a new version; old objects and metadata remain. Existing ready sources are versioned on the next refresh, and extraction can migrate one current source before use.

Published facts and confirmed decision evidence carry `sourceVersionId` and `spanId`. Each span records its exact quote under the immutable version. `GET /api/v1/projects/{projectId}/sources/{sourceId}/versions/{versionId}` reads and checks the saved object hash. `GET .../spans/{spanId}` rechecks the stored quote and stable span ID against that version. Legacy verified facts are upgraded on reuse without invoking Gemini again.

## Checks completed

- 131 Python tests passed, 10 skipped, plus 13 subtests. The Firestore emulator test used an in-memory Cloud Storage stand-in to verify an edited Doc retains both versions and both cited spans after the old published fact is replaced. It also checked that a retry writes one version and that legacy fact citation migration reuses a verified result.
- TypeScript typecheck and lint passed.

## Real-service merge gate

Leave the PR open until the running app and Google services pass these steps:

1. Refresh a synthetic Google Doc in the connected Drive folder and confirm version 1 in Firestore and Cloud Storage.
2. Create or confirm a quote-backed decision and extract a verified fact. Resolve both citation spans through the API against version 1.
3. Edit the synthetic Doc, refresh it again, and confirm version 2 differs. Read both versions and the old/new spans; each quote must match the saved text at its reported offsets.
4. Submit a duplicate refresh and verify one version per unique text. Submit an absent or ambiguous quote and verify publication fails with a clear error.
5. Recheck the deployed decision, review, and graph path after merge. Record worker failure/retry and native permission limits separately under KAN-11/KAN-23.
