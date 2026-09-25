# Decision Radar
Decision Radar is an organisational-memory and decision-intelligence product for project teams. It connects to Google Workspace, preserves the evidence and rationale behind decisions, detects when new information challenges their assumptions, and uses an interactive impact graph to show the downstream consequences.

This repository currently contains the design for a two-person, three-week AI Builder Cup 2026 MVP. Development is scheduled from 25 September through 15 October 2026. No application has been implemented or deployed.

- [High-level design](docs/HLD.md): product scope, architecture, Google services, tradeoffs, success criteria, and delivery plan.
- [Low-level design (Full Vision)](docs/LLD.md): full production-grade entities, APIs, processing steps, comparison rules, review states, reliability, and validation.
- [Low-level design (MVP Prototype)](docs/LLD_MVP.md): streamlined implementation contract tailored to the 14 active sprint tasks and competition demo.

## Project tracking

- [KAN Jira board](https://geminimaxxing.atlassian.net/jira/software/projects/KAN/boards/1): implementation tickets, acceptance criteria, dependencies, and the `back-burner` backlog.
- [Decision Radar project hub](https://geminimaxxing.atlassian.net/wiki/spaces/GeminiMaxx/overview): product overview, MVP architecture, trust principles, and prototype completion criteria.
- [MVP scope, delivery plan & backlog](https://geminimaxxing.atlassian.net/wiki/spaces/GeminiMaxx/pages/163960/MVP+Scope+Delivery+Plan+Backlog): two-person milestones, ownership, MVP boundaries, and deferred work.

The design describes Decision Radar as a Next.js/React and Google Workspace-connected MVP. The user connects and selects project sources once; routine input comes from background synchronization. Other implementation choices remain proposals.

Start with the HLD. The LLD provides the implementation contract for the proposed MVP.
