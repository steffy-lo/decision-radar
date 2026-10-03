# KAN-9 dependency storage and impact projection

Implemented on `codex/kan9-impact-api`, based on `origin/main` at `a1f6667`.
KAN-17 remains a dependency for live decision confirmation and assessment output.
This branch uses the shared models already on main and does not stack on the KAN-17 draft.

## API

All routes use `/api/v1/projects/{projectId}` and require a verified Firebase bearer
token plus project membership. Editors and administrators can create edges; viewers
can read the graph. Responses use `Cache-Control: private, no-store`.

| Method | Route | Result |
| --- | --- | --- |
| GET | `/dependencies` | Current graph revision and persisted dependencies; revision also returned as ETag. |
| POST | `/dependencies` | Create an `enables` or `requires_review_of` edge between active project decisions. |
| GET | `/alerts/{alertId}/graph` | Direct finding, challenged decision, downstream decisions, dependency edges, and all affected paths. |

POST requires a UUID `Idempotency-Key` and `If-Match: "<graph revision>"`. An empty
graph starts at revision 0. The body uses `fromDecisionId`, `toDecisionId`,
`relationType`, and `impactDescription`. Both relationships propagate in the stored
direction, from the challenged prerequisite to the decision requiring review.

The graph revision is separate from KAN-17's decision revision. Clients must GET
`/dependencies` before writing and reload after `REVISION_CONFLICT` (409).
The same key, body, and revision replay the original response for 24 hours, even
after a later graph change. Reusing a key with different inputs returns 409.
Expired receipts no longer bypass revision checks. A repeat edge with the same
description returns the existing edge without advancing the graph revision.
Changing an existing description returns `DEPENDENCY_EXISTS` (409); edge editing
and deletion are outside this implementation.

## Storage and safety

Edges are stored under `projects/{projectId}/dependencies/{edgeId}`. Deterministic
IDs include the project, endpoint IDs, and relationship type. Idempotency receipts
use `dependencyRequests/{uuid}`; `graphState/current` stores the revision.

Every new edge transaction reads the complete graph and both endpoint decisions,
validates the DAG with Kahn's algorithm, then writes the edge, graph revision, and
receipt atomically. All graph writers must read and write the same state document.
This serializes concurrent opposing edges even when their edge IDs differ. Direct
Firestore writes outside this adapter would bypass the invariant; browser Firestore
rules already deny direct access.

Self-edges and cycles return 422. Missing project decisions return 404, and draft or
retired endpoints return 409. SDK transaction retries are followed by bounded
backoff for exhausted lock contention. Continued contention returns `GRAPH_BUSY`
(503) with `Retry-After: 1`; clients can retry the same request safely.

The MVP limit is 500 stored dependency edges and 1,000 affected paths per projection.
An oversized graph or projection returns an explicit 422 instead of silently
omitting paths. Receipts expire logically after 24 hours; physical deletion or a
Firestore TTL policy is not configured by this branch.

## Projection contract

Reads run in a Firestore transaction so the graph revision, alert, finding,
assumption, and decision records form one consistent snapshot.

- `rootId` identifies the directly challenged decision; `findingId` identifies the
  finding node.
- The finding node has `nodeType: finding` and `impact: direct_challenge`. Its
  `finding` includes the typed values, reason code, delta, and both evidence references.
- Decision nodes have `nodeType: decision`. Only the root has
  `impact: direct_challenge`; all reachable active decisions have
  `impact: downstream_impact` and carry no finding or evidence fields.
- The finding-to-root edge has `edgeType: direct_challenge` and no dependency
  relationship. Stored edges have `edgeType: dependency`, their relationship type,
  and the human-authored impact description.
- Each `affectedPaths` entry names its affected decision, ordered node IDs starting
  at the finding, and ordered edge IDs. A diamond keeps both paths while returning
  each node and edge only once. Ordering is deterministic.

Only contradictory findings tied to an active assumption on the alert's current
active decision revision can trigger a projection. Stale roots return 409. Draft
and retired downstream decisions stop traversal. Missing dependency endpoints and
corrupt graphs fail closed. The service does not generate findings, create alerts,
or change decisions or reviews.

The adapter accepts the KAN-17 draft's `version`/`pendingRationale` decision
metadata and `entityId` assumption metadata while preserving the shared domain
contract. The Next.js proxy forwards ETag. API authentication is declared as HTTP
Bearer so Swagger can send verified tokens through its Authorize control.

## Validation on 3 October 2026

- Nine domain tests cover the vendor fixture, both relationships, diamond paths,
  deterministic ordering, isolated roots, lifecycle filtering, stale challenges,
  cycle/self-edge rejection, project isolation, missing endpoints, and path limits.
- Nine opt-in Firestore emulator/API tests cover persistence, eight simultaneous
  request replays, opposing edge races, changed and expired keys, rejected writes,
  editor/viewer/nonmember authorization, required headers, ETag, and projections
  from records shaped like the KAN-17 draft.
- Final validation passed: 30 service/domain/emulator/API tests, six shared Python
  contract tests, three TypeScript contract tests, web lint, and TypeScript checking.
  The knowledge graph was refreshed with `graphify update .` (AST only).

Run the storage/API suite against a local emulator only:

```sh
KAN9_TEST_FIRESTORE_EMULATOR=127.0.0.1:8080 \
  services/radar/.venv/bin/python -m unittest services.radar.tests.test_impact_emulator -v
```

### Hands-on UAT

The actual API was run locally at port 8019, with a Firebase Auth emulator test
user and synthetic fixture records in a separate `demo-kan9` Firestore project.
No authentication or storage dependencies were replaced during browser UAT.
The API has no product graph UI yet, so its Swagger browser form was the nearest
available integration path.

| Browser action | Observed result |
| --- | --- |
| Sign in using Swagger Authorize and create launch → testing (`enables`) | 201, ETag/revision 1. |
| Replay the same key/body/revision | 201, same edge ID and revision 1. |
| Create testing → production (`requires_review_of`) | 201, ETag/revision 2. |
| Attempt production → launch | 422 `DEPENDENCY_CYCLE`. |
| Attempt launch → launch | 422 `SELF_DEPENDENCY`. |
| Fetch the fixture alert graph | 200; direct 14-day finding with baseline/update quotes; testing and production marked downstream; two affected paths. |
| Read dependencies after rejected writes | 200; exactly two stored edges and revision 2. |

The first UAT request revealed Swagger's reserved Authorization-header limitation.
Declaring HTTP Bearer authentication fixed it; authenticated creation and all graph
checks above then passed. The initial eight-request concurrency test also exposed
exhausted emulator transaction retries; bounded backoff fixed the rerun.

## Remaining integration checks

1. After KAN-4, KAN-16, and KAN-17 land, rebase this branch on main and run the full
   KAN-3 → Drive snapshots → extraction → confirmation → assessment → impact flow.
   Use root Doc, TXT, nested Doc, and saved Meet transcript sources. Seeded fixture
   records and compatibility with draft storage metadata do not establish this.
2. Verify projections against findings and active revisions published by the
   merged KAN-17 implementation, including a revised/retired decision and an edited
   source. The current check deliberately rejects stale direct challenges.
3. The main branch has project membership authorization but no per-viewer native
   Workspace source access service. Integrate that permission check before serving
   live private evidence through this endpoint; project membership alone does not
   satisfy the LLD's native-source permission invariant.
4. KAN-19 must consume this projection contract and provide the interactive product
   graph. KAN-19 rendering and full product UI UAT are not covered here.

KAN-9 is started and its core is testable independently. It should remain open
until the live dependency and permission checks pass.
