# Decision Radar
Decision Radar is an organisational-memory and decision-intelligence product for project teams. It connects to Google Workspace, preserves the evidence and rationale behind decisions, detects when new information challenges their assumptions, and uses an interactive impact graph to show the downstream consequences.

- [High-level design](docs/HLD.md): product scope, architecture, Google services, tradeoffs, success criteria, and delivery plan.
- [Low-level design (Full Vision)](docs/LLD.md): full production-grade entities, APIs, processing steps, comparison rules, review states, reliability, and validation.
- [Low-level design (MVP Prototype)](docs/LLD_MVP.md): streamlined implementation contract tailored to the 14 active sprint tasks and competition demo.
- Original design attachments: [HLD v0.4](docs/reference/archive/2026-09-21/HLD-v0.4.pdf) and [LLD v0.4](docs/reference/archive/2026-09-21/LLD-v0.4.pdf).
- [AI Builder Cup submission notes](docs/AI_BUILDER_CUP.md): official deadline, prototype requirements, and judging weights.
- [Vendor-delay demo fixture](fixtures/README.md): shared Python/TypeScript contract and synthetic evidence path.

## Project Tracking

- [KAN Jira board](https://geminimaxxing.atlassian.net/jira/software/projects/KAN/boards/1): implementation tickets, acceptance criteria, dependencies, and the `back-burner` backlog.
- [Decision Radar project hub](https://geminimaxxing.atlassian.net/wiki/spaces/GeminiMaxx/overview): product overview, MVP architecture, trust principles, and prototype completion criteria.
- [MVP scope, delivery plan & backlog](https://geminimaxxing.atlassian.net/wiki/spaces/GeminiMaxx/pages/163960/MVP+Scope+Delivery+Plan+Backlog): two-person milestones, ownership, MVP boundaries, and deferred work.
- [Graphify guide](graphify-out/README.md): how to query, update, and share the repository knowledge graph.

---

## Codebase Layout

```text
apps/web/                                # Next.js App Router (React + TypeScript)
  src/app/
    api/v1/[...path]/route.ts            # Node.js proxy route forwarding to FastAPI
    page.tsx                             # Prototype welcome page
    projects/[id]/                       # Decision register, sources, reviews, briefs
    api/v1/projects/[id]/fixture/route.ts # Validated synthetic project API
  src/lib/
    api/client.ts                        # Typed API client calling /api/v1

services/radar/                          # Python Core Backend (FastAPI + Worker)
  api/
    main.py                              # FastAPI entrypoint, middleware, CORS
    deps.py                              # Firebase auth and project-membership dependencies
    routes/projects.py                   # Protected project membership endpoint
    routes/health.py                     # GET /health & GET /api/v1/health
  domain/models.py                       # Pydantic domain models
  adapters/firestore.py                  # Firestore async client wrapper
  worker/tasks.py                        # Background worker entrypoint
  config.py                              # Pydantic Settings (fail-fast env config)

infra/                                   # Infrastructure & Firebase Emulator configs
  firebase.json                          # Firebase emulator suite (Firestore, Auth, Storage)
  firestore.rules                        # Firestore security rules
  firestore.indexes.json                 # Firestore composite indexes
```

---

## Local Development Quickstart

### Prerequisites
- Python 3.10+
- Node.js 20.9+ and npm
- Firebase CLI (`npm i -g firebase-tools`)

### 1. Set Up Python Virtual Environment & Install Dependencies
```bash
cd services/radar
python3 -m venv .venv
source .venv/bin/activate
cp .env.example .env
pip install -r requirements.txt
```

### 2. Install Web Dependencies
```bash
cd apps/web
npm install
```

### 2a. Configure Firebase

- Copy `apps/web/.env.example` to `apps/web/.env.local` and supply the Firebase
  web app values. For local emulators, retain the Auth emulator URL.
- Copy `services/radar/.env.example` to `services/radar/.env`. This is where the
  API reads `FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099` and
  `FIRESTORE_EMULATOR_HOST=127.0.0.1:8080` for local emulators.
- Production uses Application Default Credentials or its configured service
  account to verify Firebase ID tokens.

### 3. Run Services Locally

#### Start Firebase Emulators
```bash
npm run emulators
# UI available at http://localhost:4000
```

The command starts all emulators with the `decision-radar` project ID,
which must match `FIREBASE_PROJECT_ID` and `NEXT_PUBLIC_FIREBASE_PROJECT_ID`.

#### Start FastAPI API Backend
```bash
npm run dev:api
# API available at http://localhost:8000 (Swagger docs at /docs)
```

#### Start Background Worker
```bash
npm run dev:worker
```

#### Start Next.js Web Application
```bash
npm run dev:web
# Web UI available at http://localhost:3000
```
