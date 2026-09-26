# Graph Report - kan27-graphify  (2026-09-26)

## Corpus Check
- Corpus is ~9,670 words - fits in a single context window. You may not need a graph.

## Summary
- 168 nodes · 166 edges · 25 communities (15 shown, 10 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 9 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `703d67e8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- API Authentication
- Product Architecture
- Web Dependencies
- TypeScript Configuration
- API Proxy Routes
- Backend Configuration
- Web Linting
- Monorepo Scripts
- Web Client
- Firestore Adapter
- Development Scripts
- Project Documentation
- Backend Service Contracts
- Web Brand Assets
- FastAPI Dependencies
- Agent Guidance
- PostCSS Setup
- File Icon
- Globe Icon
- Window Icon
- Assessment Service
- Firestore Client
- HTTP Client
- Environment Configuration

## God Nodes (most connected - your core abstractions)
1. `compilerOptions` - 16 edges
2. `Decision Radar High-Level Design` - 8 edges
3. `Decision Radar MVP Prototype Design` - 7 edges
4. `scripts` - 5 edges
5. `scripts` - 5 edges
6. `next` - 4 edges
7. `Decision Radar` - 4 edges
8. `Deterministic Typed Comparison` - 4 edges
9. `HealthResponse` - 3 edges
10. `Settings` - 3 edges

## Surprising Connections (you probably didn't know these)
- `Next.js Web Project` --conceptually_related_to--> `Next.js Wordmark`  [INFERRED]
  apps/web/README.md → apps/web/public/next.svg
- `Next.js Web Project` --conceptually_related_to--> `Vercel Triangle Mark`  [INFERRED]
  apps/web/README.md → apps/web/public/vercel.svg
- `Google Workspace Ingestion` --semantically_similar_to--> `Single-Folder Drive Ingestion`  [INFERRED] [semantically similar]
  docs/HLD.md → docs/LLD_MVP.md
- `Typed Comparison Rules` --semantically_similar_to--> `Deterministic Typed Comparison`  [INFERRED] [semantically similar]
  docs/HLD.md → docs/LLD_MVP.md
- `EvidenceValidator` --semantically_similar_to--> `Quote-Containment Validation`  [INFERRED] [semantically similar]
  docs/LLD.md → docs/LLD_MVP.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Evidence-to-Decision Review Pipeline** — docs_hld_google_workspace_ingestion, docs_hld_gemini_vertex_ai, docs_hld_typed_comparison_rules, docs_hld_evidence_traceability, docs_hld_impact_graph, docs_hld_human_in_the_loop_review [EXTRACTED 1.00]
- **MVP Validated Demo Flow** — docs_lld_mvp_single_folder_ingestion, docs_lld_mvp_quote_containment_validation, docs_lld_mvp_deterministic_typed_comparison, docs_lld_mvp_synthetic_demo_fixture, docs_lld_mvp_human_review_workflow [EXTRACTED 1.00]

## Communities (25 total, 10 thin omitted)

### Community 0 - "API Authentication"
Cohesion: 0.12
Nodes (17): datetime, fastapi, fastapi_middleware_cors, pydantic, Stub dependency for Firebase JWT authentication. Will be implemented in KAN-2., verify_firebase_token(), get, root() (+9 more)

### Community 1 - "Product Architecture"
Cohesion: 0.12
Nodes (20): Decision Radar High-Level Design, Evidence Traceability, Firestore and Cloud Storage, Gemini on Vertex AI, Google Workspace Ingestion, Human-in-the-Loop Review, Evidence-Backed Impact Graph, Organisational Memory and Decision Intelligence (+12 more)

### Community 2 - "Web Dependencies"
Cohesion: 0.11
Nodes (17): eslintConfig, dependencies, next, react, react-dom, name, private, version (+9 more)

### Community 3 - "TypeScript Configuration"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 4 - "API Proxy Routes"
Cohesion: 0.12
Nodes (11): nextConfig, DELETE, GET, PATCH, POST, PUT, apps_web_src_app_globals, geistMono (+3 more)

### Community 5 - "Backend Configuration"
Cohesion: 0.22
Nodes (9): BaseSettings, pathlib, pydantic_settings, get_settings(), Settings, Worker entrypoint process for background ingestion and assessment jobs., run_worker(), sys (+1 more)

### Community 6 - "Web Linting"
Cohesion: 0.22
Nodes (9): devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node, @types/react, @types/react-dom (+1 more)

### Community 7 - "Monorepo Scripts"
Cohesion: 0.22
Nodes (8): name, private, scripts, dev:api, dev:web, dev:worker, emulators, version

### Community 8 - "Web Client"
Cohesion: 0.53
Nodes (4): Home(), checkBackendHealth(), HealthResponse, react

### Community 9 - "Firestore Adapter"
Cohesion: 0.33
Nodes (5): AsyncClient, google_cloud, os, get_firestore_client(), Returns a Firestore AsyncClient configured for production or local emulator.

### Community 10 - "Development Scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, lint, start

### Community 11 - "Project Documentation"
Cohesion: 0.40
Nodes (5): Decision Radar, Graphify Guide, High-Level Design, Low-Level Design (Full Vision), Low-Level Design (MVP Prototype)

### Community 12 - "Backend Service Contracts"
Cohesion: 0.50
Nodes (4): Full Production Implementation Contract, Decision Radar Low-Level Design, Idempotency and Optimistic Locking, JobService

### Community 13 - "Web Brand Assets"
Cohesion: 0.67
Nodes (3): Next.js Wordmark, Vercel Triangle Mark, Next.js Web Project

### Community 14 - "FastAPI Dependencies"
Cohesion: 0.67
Nodes (3): FastAPI, Pydantic, Uvicorn

## Knowledge Gaps
- **84 isolated node(s):** `eslintConfig`, `next`, `react`, `react-dom`, `name` (+79 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 108 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `next` connect `API Proxy Routes` to `Web Dependencies`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `devDependencies` connect `Web Linting` to `Web Dependencies`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `react` connect `Web Client` to `Web Dependencies`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **What connects `eslintConfig`, `next`, `react` to the rest of the system?**
  _84 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `API Authentication` be split into smaller, more focused modules?**
  _Cohesion score 0.11904761904761904 - nodes in this community are weakly interconnected._
- **Should `Product Architecture` be split into smaller, more focused modules?**
  _Cohesion score 0.11578947368421053 - nodes in this community are weakly interconnected._
- **Should `Web Dependencies` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._