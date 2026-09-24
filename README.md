# Decision Radar
Decision Radar is an organisational-memory and decision-intelligence product for project teams. It connects to Google Workspace, preserves the evidence and rationale behind decisions, detects when new information challenges their assumptions, and uses an interactive impact graph to show the downstream consequences.

This repository currently contains the design for a two-person, three-week AI Builder Cup 2026 MVP. Development is scheduled from 25 September through 15 October 2026. No application has been implemented or deployed.

- [High-level design](docs/HLD.md): product scope, architecture, Google services, tradeoffs, success criteria, and delivery plan.
- [Low-level design](docs/LLD.md): entities, APIs, processing steps, comparison rules, review states, reliability, and validation.

The design describes Decision Radar as a Next.js/React and Google Workspace-connected MVP. The user connects and selects project sources once; routine input comes from background synchronization. Other implementation choices remain proposals.

Start with the HLD. The LLD provides the implementation contract for the proposed MVP.
