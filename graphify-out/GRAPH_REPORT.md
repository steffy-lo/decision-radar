# Graph Report - ai-builder-cup-2026  (2026-09-27)

## Corpus Check
- 35 files · ~10,865 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 3, .rules 2, .ico 1)

## Summary
- 243 nodes · 299 edges · 26 communities (16 shown, 10 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `66bd7713`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.py
- Decision Radar High-Level Design
- web/package.json
- compilerOptions
- config.py
- route.ts
- devDependencies
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
- deps.py

## God Nodes (most connected - your core abstractions)
1. `compilerOptions` - 16 edges
2. `authenticate_bearer()` - 12 edges
3. `require_project_member()` - 9 edges
4. `FakeSnapshot` - 8 edges
5. `Decision Radar High-Level Design` - 8 edges
6. `Decision Radar MVP Prototype Design` - 7 edges
7. `getFirebaseAuth()` - 6 edges
8. `AuthenticatedProjectMember` - 6 edges
9. `FakeDocument` - 6 edges
10. `AuthenticationTests` - 6 edges

## Surprising Connections (you probably didn't know these)
- `Next.js Web Project` --conceptually_related_to--> `Next.js Wordmark`  [INFERRED]
  apps/web/README.md → apps/web/public/next.svg
- `Next.js Web Project` --conceptually_related_to--> `Vercel Triangle Mark`  [INFERRED]
  apps/web/README.md → apps/web/public/vercel.svg
- `Google Workspace Ingestion` --semantically_similar_to--> `Single-Folder Drive Ingestion`  [INFERRED] [semantically similar]
  docs/HLD.md → docs/LLD_MVP.md
- `Typed Comparison Rules` --semantically_similar_to--> `Deterministic Typed Comparison`  [INFERRED] [semantically similar]
  docs/HLD.md → docs/LLD_MVP.md
- `Comparator` --semantically_similar_to--> `Deterministic Typed Comparison`  [INFERRED] [semantically similar]
  docs/LLD.md → docs/LLD_MVP.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Effective Graphify Workflow** — agents_graphify_query_first, agents_graphify_wiki_navigation, agents_graphify_dirty_output_policy, agents_graphify_ast_update_after_code_changes [EXTRACTED 1.00]
- **Evidence-to-Decision Review Pipeline** — docs_hld_google_workspace_ingestion, docs_hld_gemini_vertex_ai, docs_hld_typed_comparison_rules, docs_hld_evidence_traceability, docs_hld_impact_graph, docs_hld_human_in_the_loop_review [EXTRACTED 1.00]
- **MVP Validated Demo Flow** — docs_lld_mvp_single_folder_ingestion, docs_lld_mvp_quote_containment_validation, docs_lld_mvp_deterministic_typed_comparison, docs_lld_mvp_synthetic_demo_fixture, docs_lld_mvp_human_review_workflow [EXTRACTED 1.00]

## Communities (26 total, 10 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.15
Nodes (13): datetime, fastapi, fastapi_middleware_cors, middleware, pydantic, prevent_private_api_caching(), get, root() (+5 more)

### Community 1 - "Decision Radar High-Level Design"
Cohesion: 0.12
Nodes (20): Decision Radar High-Level Design, Evidence Traceability, Firestore and Cloud Storage, Gemini on Vertex AI, Google Workspace Ingestion, Human-in-the-Loop Review, Evidence-Backed Impact Graph, Organisational Memory and Decision Intelligence (+12 more)

### Community 2 - "web/package.json"
Cohesion: 0.08
Nodes (23): eslintConfig, dependencies, firebase, next, react, react-dom, name, private (+15 more)

### Community 3 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 4 - "config.py"
Cohesion: 0.18
Nodes (10): BaseSettings, model_validator, pathlib, pydantic_settings, get_settings(), Settings, Worker entrypoint process for background ingestion and assessment jobs., run_worker() (+2 more)

### Community 5 - "route.ts"
Cohesion: 0.11
Nodes (15): nextConfig, DELETE, FORWARDED_REQUEST_HEADERS, FORWARDED_RESPONSE_HEADERS, GET, PATCH, POST, privateJson() (+7 more)

### Community 6 - "devDependencies"
Cohesion: 0.22
Nodes (9): devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node, @types/react, @types/react-dom (+1 more)

### Community 7 - "package.json"
Cohesion: 0.17
Nodes (11): devDependencies, firebase-tools, name, private, scripts, dev:api, dev:web, dev:worker (+3 more)

### Community 8 - "Repository Graphify Instructions"
Cohesion: 0.47
Nodes (6): AST Graph Update After Code Changes, Dirty Graph Output Policy, Query the Knowledge Graph First, Repository Graphify Instructions, Use Graphify Instructions on /graphify, Graph Wiki Navigation

### Community 9 - "client.ts"
Cohesion: 0.20
Nodes (13): Home(), AuthGate(), AuthenticationRequiredError, checkBackendHealth(), fetchPrivateApi(), getCurrentProjectMembership(), HealthResponse, ProjectMembership (+5 more)

### Community 10 - "authenticate_bearer"
Cohesion: 0.09
Nodes (16): Any, HTTPException, authenticate_bearer(), extract_bearer_token(), Validate the Authorization header without trusting its token contents., Verify a bearer token and normalize Firebase failures into a 401 response., FastAPI dependency that returns only verified Firebase claims., unauthorized() (+8 more)

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

### Community 25 - "deps.py"
Cohesion: 0.11
Nodes (23): App, AsyncClient, firebase_admin, functools, google_cloud, os, get_firebase_app(), Firebase Admin initialization for server-side ID token verification. (+15 more)

## Knowledge Gaps
- **91 isolated node(s):** `eslintConfig`, `nextConfig`, `name`, `version`, `private` (+86 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 136 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `next` connect `route.ts` to `web/package.json`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Why does `authenticate_bearer()` connect `authenticate_bearer` to `deps.py`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `devDependencies` connect `devDependencies` to `web/package.json`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **What connects `eslintConfig`, `nextConfig`, `name` to the rest of the system?**
  _91 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Decision Radar High-Level Design` be split into smaller, more focused modules?**
  _Cohesion score 0.11578947368421053 - nodes in this community are weakly interconnected._
- **Should `web/package.json` be split into smaller, more focused modules?**
  _Cohesion score 0.08333333333333333 - nodes in this community are weakly interconnected._
- **Should `compilerOptions` be split into smaller, more focused modules?**
  _Cohesion score 0.10526315789473684 - nodes in this community are weakly interconnected._