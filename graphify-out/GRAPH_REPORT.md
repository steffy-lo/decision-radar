# Graph Report - decision-radar-kan17  (2026-09-28)

## Corpus Check
- 66 files · ~19,679 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 4, .rules 2, .ico 1)

## Summary
- 492 nodes · 855 edges · 37 communities (21 shown, 16 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 68 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `45ad4474`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Extractor
- Decision Radar High-Level Design
- web/package.json
- compilerOptions
- models.py
- [...path]/route.ts
- models.ts
- package.json
- Repository Graphify Instructions
- client.ts
- deps.py
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
- vendor-delay.json
- test_contract.mjs
- AI_BUILDER_CUP.md
- KAN16_EXTRACTION.md
- pipeline/__init__.py
- assessment.py
- Assumption
- AssessmentTests
- apps_web_node_modules_typescript_lib_typescript

## God Nodes (most connected - your core abstractions)
1. `RadarModel` - 25 edges
2. `Assumption` - 17 edges
3. `compilerOptions` - 16 edges
4. `Fact` - 16 edges
5. `Extractor` - 16 edges
6. `fail()` - 15 edges
7. `ExtractionTests` - 15 edges
8. `DecisionService` - 14 edges
9. `AssessmentService` - 13 edges
10. `authenticate_bearer()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `AssessmentTests` --uses--> `AssessmentService`  [INFERRED]
  tests/test_assessment.py → services/radar/domain/assessment.py
- `ExtractionTests` --uses--> `ExtractionError`  [INFERRED]
  tests/test_extraction.py → services/radar/pipeline/extraction.py
- `ExtractionTests` --uses--> `VertexGeminiGenerator`  [INFERRED]
  tests/test_extraction.py → services/radar/pipeline/gemini.py
- `ComparatorTests` --uses--> `Comparator`  [INFERRED]
  tests/test_assessment.py → services/radar/domain/comparison.py
- `DecisionLifecycleTests` --uses--> `RevisionConflict`  [INFERRED]
  tests/test_assessment.py → services/radar/domain/decisions.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Effective Graphify Workflow** — agents_graphify_query_first, agents_graphify_wiki_navigation, agents_graphify_dirty_output_policy, agents_graphify_ast_update_after_code_changes [EXTRACTED 1.00]
- **Evidence-to-Decision Review Pipeline** — docs_hld_google_workspace_ingestion, docs_hld_gemini_vertex_ai, docs_hld_typed_comparison_rules, docs_hld_evidence_traceability, docs_hld_impact_graph, docs_hld_human_in_the_loop_review [EXTRACTED 1.00]
- **MVP Validated Demo Flow** — docs_lld_mvp_single_folder_ingestion, docs_lld_mvp_quote_containment_validation, docs_lld_mvp_deterministic_typed_comparison, docs_lld_mvp_synthetic_demo_fixture, docs_lld_mvp_human_review_workflow [EXTRACTED 1.00]

## Communities (37 total, 16 thin omitted)

### Community 0 - "Extractor"
Cohesion: 0.22
Nodes (8): EvidenceValidator, Extractor, Resolve an exact, unambiguous quote to one immutable snapshot span., Validate one source's Gemini candidates before handing facts to KAN-17.…, ExtractionTests, fact(), FakeGenerator, unittest_mock

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
Cohesion: 0.08
Nodes (37): calendar, decimal, hashlib, json, Protocol, pydantic_alias_generators, re, Brief (+29 more)

### Community 5 - "[...path]/route.ts"
Cohesion: 0.10
Nodes (13): nextConfig, DELETE, FORWARDED_REQUEST_HEADERS, FORWARDED_RESPONSE_HEADERS, GET, PATCH, POST, privateJson() (+5 more)

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

### Community 10 - "deps.py"
Cohesion: 0.06
Nodes (37): Any, App, AsyncClient, fastapi, firebase_admin, functools, google_cloud, HTTPException (+29 more)

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
Cohesion: 0.09
Nodes (20): BaseSettings, fastapi_middleware_cors, middleware, pydantic, pydantic_settings, prevent_private_api_caching(), get, root() (+12 more)

### Community 26 - "decision-register.tsx"
Cohesion: 0.11
Nodes (21): AppShell(), items, DecisionCard(), DecisionRegister(), displayDate(), ReviewsWorkspace(), SourcesWorkspace(), EmptyState() (+13 more)

### Community 27 - "vendor-delay.json"
Cohesion: 0.11
Nodes (15): runtime, demoFixture, alerts, assumptions, briefs, decisions, dependencies, exports (+7 more)

### Community 28 - "test_contract.mjs"
Cohesion: 0.25
Nodes (6): ref_apps_web_node_modules_typescript_lib_typescript_js, ref_node_assert, ref_node_fs, ref_node_test, fixture, source

### Community 33 - "assessment.py"
Cohesion: 0.09
Nodes (27): copy, dataclasses, datetime, pathlib, AssessmentManifest, AssessmentResult, AssessmentService, ComparisonBatch (+19 more)

### Community 34 - "Assumption"
Cohesion: 0.23
Nodes (16): _check_assumptions(), _check_version(), DecisionService, DecisionState, InvalidDecisionTransition, ValueError, Decision revision and confirmation rules independent of storage., The caller edited an older decision version. (+8 more)

## Knowledge Gaps
- **122 isolated node(s):** `eslintConfig`, `nextConfig`, `name`, `version`, `private` (+117 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 223 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `next` connect `[...path]/route.ts` to `decision-register.tsx`, `web/package.json`, `vendor-delay.json`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Why does `react` connect `decision-register.tsx` to `client.ts`, `web/package.json`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `Fact` connect `assessment.py` to `Extractor`, `models.py`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `Assumption` (e.g. with `AssessmentService` and `_record_fingerprint()`) actually correct?**
  _`Assumption` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Fact` (e.g. with `AssessmentService` and `_record_fingerprint()`) actually correct?**
  _`Fact` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Extractor` (e.g. with `Fact` and `Source`) actually correct?**
  _`Extractor` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `eslintConfig`, `nextConfig`, `name` to the rest of the system?**
  _122 weakly-connected nodes found - possible documentation gaps or missing edges._