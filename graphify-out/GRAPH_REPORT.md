# Graph Report - decision-radar-kan17  (2026-09-28)

## Corpus Check
- 70 files · ~20,885 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 4, .rules 2, .ico 1)

## Summary
- 558 nodes · 1028 edges · 41 communities (25 shown, 16 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 87 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f2450330`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_assessment_store.py
- Decision Radar High-Level Design
- web/package.json
- compilerOptions
- models.py
- [...path]/route.ts
- models.ts
- package.json
- Repository Graphify Instructions
- client.ts
- authenticate_bearer
- Decision Radar
- Decision Radar Low-Level Design
- Next.js Web Project
- FastAPI
- Next.js Agent Rules
- postcss.config.mjs
- Document File Icon
- Globe Icon
- Browser Window Icon
- AssessmentService
- Google Cloud Firestore Client
- HTTPX
- python-dotenv
- config.py
- decision-register.tsx
- assessment_store.py
- test_contract.mjs
- AI_BUILDER_CUP.md
- KAN16_EXTRACTION.md
- pipeline/__init__.py
- assessment.py
- FakeSnapshot
- test_assessment_api.py
- apps_web_node_modules_typescript_lib_typescript
- main.py
- deps.py
- firebase_auth.py
- AssessmentRouteTests

## God Nodes (most connected - your core abstractions)
1. `RadarModel` - 27 edges
2. `Assumption` - 20 edges
3. `AssessmentService` - 19 edges
4. `Fact` - 19 edges
5. `compilerOptions` - 16 edges
6. `Extractor` - 16 edges
7. `fail()` - 15 edges
8. `ExtractionTests` - 15 edges
9. `FirestoreAssessmentStore` - 14 edges
10. `DecisionService` - 14 edges

## Surprising Connections (you probably didn't know these)
- `AssessmentStoreTests` --uses--> `AssessmentConflict`  [INFERRED]
  tests/test_assessment_store.py → services/radar/adapters/assessment_store.py
- `AssessmentStoreTests` --uses--> `FirestoreAssessmentStore`  [INFERRED]
  tests/test_assessment_store.py → services/radar/adapters/assessment_store.py
- `AssessmentStoreTests` --uses--> `AssessmentService`  [INFERRED]
  tests/test_assessment_store.py → services/radar/domain/assessment.py
- `run()` --calls--> `AssessmentService`  [EXTRACTED]
  tests/test_assessment_store.py → services/radar/domain/assessment.py
- `run()` --calls--> `AssessmentService`  [EXTRACTED]
  tests/test_assessment_store.py → services/radar/domain/assessment.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Effective Graphify Workflow** — agents_graphify_query_first, agents_graphify_wiki_navigation, agents_graphify_dirty_output_policy, agents_graphify_ast_update_after_code_changes [EXTRACTED 1.00]
- **Evidence-to-Decision Review Pipeline** — docs_hld_google_workspace_ingestion, docs_hld_gemini_vertex_ai, docs_hld_typed_comparison_rules, docs_hld_evidence_traceability, docs_hld_impact_graph, docs_hld_human_in_the_loop_review [EXTRACTED 1.00]
- **MVP Validated Demo Flow** — docs_lld_mvp_single_folder_ingestion, docs_lld_mvp_quote_containment_validation, docs_lld_mvp_deterministic_typed_comparison, docs_lld_mvp_synthetic_demo_fixture, docs_lld_mvp_human_review_workflow [EXTRACTED 1.00]

## Communities (41 total, 16 thin omitted)

### Community 0 - "test_assessment_store.py"
Cohesion: 0.09
Nodes (10): asyncio, AssessmentStoreTests, run(), run(), Client, Collection, Document, Snapshot (+2 more)

### Community 1 - "Decision Radar High-Level Design"
Cohesion: 0.10
Nodes (21): Decision Radar High-Level Design, Evidence Traceability, Firestore and Cloud Storage, Gemini on Vertex AI, Google Workspace Ingestion, Human-in-the-Loop Review, Evidence-Backed Impact Graph, Organisational Memory and Decision Intelligence (+13 more)

### Community 2 - "web/package.json"
Cohesion: 0.06
Nodes (32): eslintConfig, dependencies, firebase, next, react, react-dom, devDependencies, eslint (+24 more)

### Community 3 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 4 - "models.py"
Cohesion: 0.07
Nodes (45): calendar, decimal, Protocol, pydantic, pydantic_alias_generators, re, Brief, DateValue (+37 more)

### Community 5 - "[...path]/route.ts"
Cohesion: 0.10
Nodes (13): nextConfig, DELETE, FORWARDED_REQUEST_HEADERS, FORWARDED_RESPONSE_HEADERS, GET, PATCH, POST, privateJson() (+5 more)

### Community 6 - "models.ts"
Cohesion: 0.06
Nodes (47): runtime, demoFixture, DecisionView, ReviewView, Alert, Assumption, Brief, Check (+39 more)

### Community 7 - "package.json"
Cohesion: 0.17
Nodes (11): devDependencies, firebase-tools, name, private, scripts, dev:api, dev:web, dev:worker (+3 more)

### Community 8 - "Repository Graphify Instructions"
Cohesion: 0.47
Nodes (6): AST Graph Update After Code Changes, Dirty Graph Output Policy, Query the Knowledge Graph First, Repository Graphify Instructions, Use Graphify Instructions on /graphify, Graph Wiki Navigation

### Community 9 - "client.ts"
Cohesion: 0.21
Nodes (10): AuthGate(), AuthenticationRequiredError, fetchPrivateApi(), getCurrentProjectMembership(), HealthResponse, ProjectMembership, config, getFirebaseApp() (+2 more)

### Community 10 - "authenticate_bearer"
Cohesion: 0.19
Nodes (7): authenticate_bearer(), Any, Verify a bearer token and normalize Firebase failures into a 401 response., FastAPI dependency that returns only verified Firebase claims., verify_firebase_token(), AuthenticationTests, TokenVerifier

### Community 11 - "Decision Radar"
Cohesion: 0.40
Nodes (5): Decision Radar, Graphify Guide, High-Level Design, Low-Level Design (Full Vision), Low-Level Design (MVP Prototype)

### Community 12 - "Decision Radar Low-Level Design"
Cohesion: 0.50
Nodes (4): Full Production Implementation Contract, Decision Radar Low-Level Design, Idempotency and Optimistic Locking, JobService

### Community 13 - "Next.js Web Project"
Cohesion: 0.67
Nodes (3): Next.js Wordmark, Vercel Triangle Mark, Next.js Web Project

### Community 14 - "FastAPI"
Cohesion: 0.67
Nodes (3): FastAPI, Pydantic, Uvicorn

### Community 25 - "config.py"
Cohesion: 0.08
Nodes (15): BaseSettings, copy, json, pathlib, pydantic_settings, get_settings(), model_validator, Settings (+7 more)

### Community 26 - "decision-register.tsx"
Cohesion: 0.11
Nodes (21): AppShell(), items, DecisionCard(), DecisionRegister(), displayDate(), ReviewsWorkspace(), SourcesWorkspace(), EmptyState() (+13 more)

### Community 27 - "assessment_store.py"
Cohesion: 0.11
Nodes (25): google_cloud, os, post, AssessmentConflict, AssessmentInputs, _assumptions(), _data(), _entities() (+17 more)

### Community 28 - "test_contract.mjs"
Cohesion: 0.25
Nodes (6): ref_apps_web_node_modules_typescript_lib_typescript_js, ref_node_assert, ref_node_fs, ref_node_test, fixture, source

### Community 33 - "assessment.py"
Cohesion: 0.07
Nodes (41): dataclasses, datetime, hashlib, get_health(), HealthResponse, BaseModel, get, AssessmentManifest (+33 more)

### Community 34 - "FakeSnapshot"
Cohesion: 0.21
Nodes (3): FakeDocument, FakeFirestore, FakeSnapshot

### Community 35 - "test_assessment_api.py"
Cohesion: 0.22
Nodes (9): fastapi_testclient, Resolve the verified user to their membership in the requested project., require_project_member(), get_current_project_member(), get, Return the verified caller's membership in the selected project., AuthenticatedProjectMember, ProjectMember (+1 more)

### Community 37 - "main.py"
Cohesion: 0.25
Nodes (7): fastapi, fastapi_middleware_cors, middleware, prevent_private_api_caching(), get, root(), uvicorn

### Community 38 - "deps.py"
Cohesion: 0.31
Nodes (7): firebase_admin, HTTPException, extract_bearer_token(), Authentication and project authorization dependencies., Validate the Authorization header without trusting its token contents., unauthorized(), typing

### Community 39 - "firebase_auth.py"
Cohesion: 0.29
Nodes (7): App, functools, get_firebase_app(), Firebase Admin initialization for server-side ID token verification., Return the process-wide Firebase Admin app for this project., Verify an ID token and return Firebase's trusted decoded claims., verify_id_token()

## Knowledge Gaps
- **122 isolated node(s):** `eslintConfig`, `nextConfig`, `name`, `version`, `private` (+117 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 240 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `next` connect `[...path]/route.ts` to `web/package.json`, `decision-register.tsx`, `models.ts`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `react` connect `decision-register.tsx` to `client.ts`, `web/package.json`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `Fact` connect `models.py` to `assessment.py`, `assessment_store.py`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Assumption` (e.g. with `AssessmentInputs` and `_assumptions()`) actually correct?**
  _`Assumption` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `AssessmentService` (e.g. with `create_assessment()` and `Comparator`) actually correct?**
  _`AssessmentService` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `Fact` (e.g. with `AssessmentInputs` and `FirestoreAssessmentStore`) actually correct?**
  _`Fact` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `eslintConfig`, `nextConfig`, `name` to the rest of the system?**
  _122 weakly-connected nodes found - possible documentation gaps or missing edges._