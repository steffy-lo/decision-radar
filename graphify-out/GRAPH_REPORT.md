# Graph Report - decision-radar-kan17  (2026-09-28)

## Corpus Check
- 73 files · ~22,447 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 4, .rules 2, .ico 1)

## Summary
- 609 nodes · 1254 edges · 44 communities (26 shown, 18 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 133 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `76a72628`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DecisionRouteTests
- Decision Radar High-Level Design
- web/package.json
- compilerOptions
- extraction.py
- vendor-delay.json
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
- assessments.py
- test_contract.mjs
- AI_BUILDER_CUP.md
- KAN16_EXTRACTION.md
- pipeline/__init__.py
- models.py
- routes/decisions.py
- deps.py
- test_assessment_store.py
- main.py
- AssessmentTests
- firebase_auth.py
- AssessmentRouteTests
- ContractTests
- pydantic
- ref_apps_web_node_modules_typescript_lib_typescript_js

## God Nodes (most connected - your core abstractions)
1. `RadarModel` - 32 edges
2. `Assumption` - 24 edges
3. `FirestoreDecisionStore` - 22 edges
4. `AuthenticatedProjectMember` - 22 edges
5. `AssessmentService` - 19 edges
6. `DecisionService` - 19 edges
7. `Fact` - 19 edges
8. `edit_decision()` - 18 edges
9. `confirm_decision()` - 17 edges
10. `EvidenceRef` - 17 edges

## Surprising Connections (you probably didn't know these)
- `AssessmentStoreTests` --uses--> `AssessmentConflict`  [INFERRED]
  tests/test_assessment_store.py → services/radar/adapters/assessment_store.py
- `FakeStore` --uses--> `AssessmentInputs`  [INFERRED]
  tests/test_assessment_api.py → services/radar/adapters/assessment_store.py
- `DecisionRouteTests` --uses--> `FirestoreDecisionStore`  [INFERRED]
  tests/test_decision_api.py → services/radar/adapters/decision_store.py
- `AssessmentTests` --uses--> `AssessmentService`  [INFERRED]
  tests/test_assessment.py → services/radar/domain/assessment.py
- `AssessmentRouteTests` --uses--> `AuthenticatedProjectMember`  [INFERRED]
  tests/test_assessment_api.py → services/radar/domain/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Effective Graphify Workflow** — agents_graphify_query_first, agents_graphify_wiki_navigation, agents_graphify_dirty_output_policy, agents_graphify_ast_update_after_code_changes [EXTRACTED 1.00]
- **Evidence-to-Decision Review Pipeline** — docs_hld_google_workspace_ingestion, docs_hld_gemini_vertex_ai, docs_hld_typed_comparison_rules, docs_hld_evidence_traceability, docs_hld_impact_graph, docs_hld_human_in_the_loop_review [EXTRACTED 1.00]
- **MVP Validated Demo Flow** — docs_lld_mvp_single_folder_ingestion, docs_lld_mvp_quote_containment_validation, docs_lld_mvp_deterministic_typed_comparison, docs_lld_mvp_synthetic_demo_fixture, docs_lld_mvp_human_review_workflow [EXTRACTED 1.00]

## Communities (44 total, 18 thin omitted)

### Community 0 - "DecisionRouteTests"
Cohesion: 0.09
Nodes (7): Client, Collection, Document, Snapshot, Transaction, DecisionRouteTests, payload()

### Community 1 - "Decision Radar High-Level Design"
Cohesion: 0.10
Nodes (21): Decision Radar High-Level Design, Evidence Traceability, Firestore and Cloud Storage, Gemini on Vertex AI, Google Workspace Ingestion, Human-in-the-Loop Review, Evidence-Backed Impact Graph, Organisational Memory and Decision Intelligence (+13 more)

### Community 2 - "web/package.json"
Cohesion: 0.06
Nodes (32): eslintConfig, dependencies, firebase, next, react, react-dom, devDependencies, eslint (+24 more)

### Community 3 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 4 - "extraction.py"
Cohesion: 0.08
Nodes (33): calendar, decimal, hashlib, json, Protocol, re, Source, CandidateGenerator (+25 more)

### Community 5 - "vendor-delay.json"
Cohesion: 0.05
Nodes (28): nextConfig, DELETE, FORWARDED_REQUEST_HEADERS, FORWARDED_RESPONSE_HEADERS, GET, PATCH, POST, privateJson() (+20 more)

### Community 6 - "models.ts"
Cohesion: 0.10
Nodes (32): DecisionView, ReviewView, Alert, Assumption, Brief, Check, choice(), decimal() (+24 more)

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
Cohesion: 0.09
Nodes (14): HTTPException, authenticate_bearer(), extract_bearer_token(), Any, Validate the Authorization header without trusting its token contents., Verify a bearer token and normalize Firebase failures into a 401 response., FastAPI dependency that returns only verified Firebase claims., unauthorized() (+6 more)

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
Cohesion: 0.20
Nodes (9): BaseSettings, pydantic_settings, get_settings(), model_validator, Settings, Worker entrypoint process for background ingestion and assessment jobs., run_worker(), sys (+1 more)

### Community 26 - "decision-register.tsx"
Cohesion: 0.11
Nodes (21): AppShell(), items, DecisionCard(), DecisionRegister(), displayDate(), ReviewsWorkspace(), SourcesWorkspace(), EmptyState() (+13 more)

### Community 27 - "assessments.py"
Cohesion: 0.18
Nodes (9): AssessmentConflict, ValueError, The request key or assessment inputs changed before publication., AssessmentRequest, create_assessment(), post, Authenticated on-demand assessment requests., FakeStore (+1 more)

### Community 28 - "test_contract.mjs"
Cohesion: 0.25
Nodes (6): apps_web_node_modules_typescript_lib_typescript, ref_node_assert, ref_node_fs, ref_node_test, fixture, source

### Community 33 - "models.py"
Cohesion: 0.07
Nodes (50): dataclasses, datetime, pydantic_alias_generators, AssessmentInputs, _assumptions(), _data(), _entities(), FirestoreAssessmentStore (+42 more)

### Community 34 - "routes/decisions.py"
Cohesion: 0.10
Nodes (49): collections_abc, Exception, patch, Response, _decision_record(), DecisionNotFound, DecisionRequestConflict, FirestoreDecisionStore (+41 more)

### Community 35 - "deps.py"
Cohesion: 0.26
Nodes (11): fastapi, firebase_admin, Authentication and project authorization dependencies., Resolve the verified user to their membership in the requested project., require_project_member(), get_current_project_member(), get, Return the verified caller's membership in the selected project. (+3 more)

### Community 36 - "test_assessment_store.py"
Cohesion: 0.23
Nodes (9): asyncio, copy, fastapi_testclient, google_cloud, pathlib, DemoFixture, model_validator, unittest (+1 more)

### Community 37 - "main.py"
Cohesion: 0.29
Nodes (6): fastapi_middleware_cors, middleware, prevent_private_api_caching(), get, root(), uvicorn

### Community 39 - "firebase_auth.py"
Cohesion: 0.24
Nodes (8): App, functools, os, get_firebase_app(), Firebase Admin initialization for server-side ID token verification., Return the process-wide Firebase Admin app for this project., Verify an ID token and return Firebase's trusted decoded claims., verify_id_token()

### Community 42 - "pydantic"
Cohesion: 0.40
Nodes (5): pydantic, get_health(), HealthResponse, BaseModel, get

## Knowledge Gaps
- **122 isolated node(s):** `eslintConfig`, `nextConfig`, `name`, `version`, `private` (+117 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 244 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `next` connect `vendor-delay.json` to `web/package.json`, `decision-register.tsx`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `AuthenticatedProjectMember` connect `deps.py` to `DecisionRouteTests`, `models.py`, `routes/decisions.py`, `test_assessment_store.py`, `AssessmentRouteTests`, `assessments.py`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `react` connect `decision-register.tsx` to `client.ts`, `web/package.json`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `Assumption` (e.g. with `AssessmentInputs` and `_assumptions()`) actually correct?**
  _`Assumption` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `FirestoreDecisionStore` (e.g. with `DecisionState` and `RevisionConflict`) actually correct?**
  _`FirestoreDecisionStore` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `AuthenticatedProjectMember` (e.g. with `create_assessment()` and `confirm_decision()`) actually correct?**
  _`AuthenticatedProjectMember` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `AssessmentService` (e.g. with `create_assessment()` and `Comparator`) actually correct?**
  _`AssessmentService` has 9 INFERRED edges - model-reasoned connections that need verification._