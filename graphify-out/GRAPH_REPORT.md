# Graph Report - decision-radar  (2026-09-28)

## Corpus Check
- 57 files · ~16,323 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 4, .rules 2, .ico 1)

## Summary
- 381 nodes · 532 edges · 31 communities (19 shown, 12 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 22 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `da3246f4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.py
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

## God Nodes (most connected - your core abstractions)
1. `RadarModel` - 19 edges
2. `compilerOptions` - 16 edges
3. `fail()` - 15 edges
4. `authenticate_bearer()` - 12 edges
5. `useProjectData()` - 10 edges
6. `next` - 9 edges
7. `isDemoProject()` - 9 edges
8. `require_project_member()` - 9 edges
9. `FakeSnapshot` - 8 edges
10. `ContractTests` - 8 edges

## Surprising Connections (you probably didn't know these)
- `ContractTests` --uses--> `DemoFixture`  [INFERRED]
  tests/test_contract.py → services/radar/domain/models.py
- `Next.js Web Project` --conceptually_related_to--> `Next.js Wordmark`  [INFERRED]
  apps/web/README.md → apps/web/public/next.svg
- `Next.js Web Project` --conceptually_related_to--> `Vercel Triangle Mark`  [INFERRED]
  apps/web/README.md → apps/web/public/vercel.svg
- `Google Workspace Ingestion` --semantically_similar_to--> `Single-Folder Drive Ingestion`  [INFERRED] [semantically similar]
  docs/HLD.md → docs/LLD_MVP.md
- `Typed Comparison Rules` --semantically_similar_to--> `Deterministic Typed Comparison`  [INFERRED] [semantically similar]
  docs/HLD.md → docs/LLD_MVP.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Effective Graphify Workflow** — agents_graphify_query_first, agents_graphify_wiki_navigation, agents_graphify_dirty_output_policy, agents_graphify_ast_update_after_code_changes [EXTRACTED 1.00]
- **Evidence-to-Decision Review Pipeline** — docs_hld_google_workspace_ingestion, docs_hld_gemini_vertex_ai, docs_hld_typed_comparison_rules, docs_hld_evidence_traceability, docs_hld_impact_graph, docs_hld_human_in_the_loop_review [EXTRACTED 1.00]
- **MVP Validated Demo Flow** — docs_lld_mvp_single_folder_ingestion, docs_lld_mvp_quote_containment_validation, docs_lld_mvp_deterministic_typed_comparison, docs_lld_mvp_synthetic_demo_fixture, docs_lld_mvp_human_review_workflow [EXTRACTED 1.00]

## Communities (31 total, 12 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.29
Nodes (6): fastapi_middleware_cors, middleware, prevent_private_api_caching(), get, root(), uvicorn

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
Nodes (33): copy, datetime, decimal, json, pathlib, pydantic, pydantic_alias_generators, get_health() (+25 more)

### Community 5 - "[...path]/route.ts"
Cohesion: 0.10
Nodes (13): nextConfig, DELETE, FORWARDED_REQUEST_HEADERS, FORWARDED_RESPONSE_HEADERS, GET, PATCH, POST, privateJson() (+5 more)

### Community 6 - "models.ts"
Cohesion: 0.10
Nodes (31): DecisionView, ReviewView, Alert, Assumption, Brief, Check, choice(), decimal() (+23 more)

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
Cohesion: 0.08
Nodes (25): Any, fastapi, firebase_admin, HTTPException, authenticate_bearer(), extract_bearer_token(), Authentication and project authorization dependencies., Validate the Authorization header without trusting its token contents. (+17 more)

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
Nodes (21): App, AsyncClient, BaseSettings, functools, google_cloud, os, pydantic_settings, get_firebase_app() (+13 more)

### Community 26 - "decision-register.tsx"
Cohesion: 0.11
Nodes (21): AppShell(), items, DecisionCard(), DecisionRegister(), displayDate(), ReviewsWorkspace(), SourcesWorkspace(), EmptyState() (+13 more)

### Community 27 - "vendor-delay.json"
Cohesion: 0.11
Nodes (16): runtime, demoFixture, parseDemoFixture(), alerts, assumptions, briefs, decisions, dependencies (+8 more)

### Community 28 - "test_contract.mjs"
Cohesion: 0.25
Nodes (6): apps_web_node_modules_typescript_lib_typescript, ref_node_assert, ref_node_fs, ref_node_test, fixture, source

## Knowledge Gaps
- **121 isolated node(s):** `eslintConfig`, `nextConfig`, `name`, `version`, `private` (+116 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 197 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `next` connect `[...path]/route.ts` to `decision-register.tsx`, `web/package.json`, `vendor-delay.json`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `react` connect `decision-register.tsx` to `client.ts`, `web/package.json`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **What connects `eslintConfig`, `nextConfig`, `name` to the rest of the system?**
  _121 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Decision Radar High-Level Design` be split into smaller, more focused modules?**
  _Cohesion score 0.1038961038961039 - nodes in this community are weakly interconnected._
- **Should `web/package.json` be split into smaller, more focused modules?**
  _Cohesion score 0.06060606060606061 - nodes in this community are weakly interconnected._
- **Should `compilerOptions` be split into smaller, more focused modules?**
  _Cohesion score 0.10526315789473684 - nodes in this community are weakly interconnected._
- **Should `models.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06871035940803383 - nodes in this community are weakly interconnected._
