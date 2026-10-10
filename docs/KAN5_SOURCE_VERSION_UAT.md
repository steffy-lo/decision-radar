# KAN-5 source version and citation check

## Storage and API

Set `SOURCE_SNAPSHOT_BUCKET=decision-radar-source-snapshots-geminimaxxing-509705` on the API and worker in staging. The bucket is in `asia-southeast1` with uniform access and public access prevention. The shared staging API/worker service account has object creation and read access; it has no object deletion role on this bucket. The bucket removed its default project-viewer reader bindings.

Refresh writes the normalised text once to a content-addressed Cloud Storage object and creates `projects/{projectId}/sources/{sourceId}/versions/{versionId}` in Firestore. The current source document points at that version while retaining the current text for the existing UI. An edited Doc gets a new version; old objects and metadata remain. Existing ready sources are versioned on the next refresh, and extraction can migrate one current source before use.

Published facts and confirmed decision evidence carry `sourceVersionId` and `spanId`. Each span records its exact quote under the immutable version. `GET /api/v1/projects/{projectId}/sources/{sourceId}/versions/{versionId}` reads and checks the saved object hash. `GET .../spans/{spanId}` rechecks the stored quote and stable span ID against that version. Legacy verified facts are upgraded on reuse without invoking Gemini again. A refresh also resolves older decision, assumption, fact, and assessment-finding evidence against the preserved version. It records `citationBackfillErrorCount` when a historical quote cannot be resolved.

## Checks completed

- 66 pytest tests passed with the Firestore emulator, plus 10 subtests. The emulator checks an edited Doc's retained versions and spans, duplicate writes, and historical decision/finding citation migration. A separate unit check covers a legacy source edited before its first versioned refresh.
- The web contract tests, TypeScript typecheck, and lint passed. The contract test checks that a versioned historical quote can outlive the current source text.

## Live UAT on 10 October 2026

- The deployed Sources page dispatched a real Cloud Tasks worker refresh for the connected synthetic Drive folder. The source library increased from 7 to 8 files when the copied Google Doc appeared.
- The copied Doc `13xBHVWl2DQhkY0KUn7okyvk1KAUAKNtuXyuaJTp8Ecw` produced version `ver_7ff31fa5fb8bedd46ebe8bd0130b5a91`. Its edited October 24 text produced `ver_c315e69bfa0cd299ed919875a94d7c56`. Both immutable objects were read back from the staging bucket with their different text. A later marker edit produced a third version and left the prior two objects readable.
- Gemini extracted the exact quote “Acme Logistics delivery date is October 24, 2026.” from version 2. The fact carries `span_45255343cb8c646ca96736afd123f22e`, and the Firestore span has the same quote and paragraph/character locator. The earlier assumption wording produced no verified fact.
- The decision form rejected a fabricated October 25 quote. The exact October 24 quote created and confirmed a synthetic decision; its saved revision has the same version/span ID as the fact. An unchanged refresh completed without creating another version.
- The existing vendor fact was re-extracted and gained a versioned span. Fresh real worker refreshes backfilled all seven historical decision revisions, all five monitored assumptions, and cached assessment findings. All eight source markers report schema 2 and zero unresolved citations.
- A local HTTP ASGI route check against real Firestore and Cloud Storage returned 200 for both prior and cited versions, 200 for the exact cited span, and 404 for an absent span. The same version/span reads through the deployed web proxy with the signed-in app's Firebase authorization returned 200 for the retained old version and cited span, and 404 for an absent span. The returned quote matched the saved October 24 text.
- The deployed Reviews page shows the baseline paragraph/character locator and update line/character locator. The graph initially rejected the new citation fields; after updating the web contract and deploying the branch image, the same alert loaded the four-step impact path. Clicking the downstream communications node showed its dependency rationale and no direct contradiction evidence.

## Real-service merge gate

Leave the PR open until the remaining checks pass:

1. Recheck the deployed decision, review, and graph path after merge. Record worker failure/retry and native permission limits separately under KAN-11/KAN-23.
