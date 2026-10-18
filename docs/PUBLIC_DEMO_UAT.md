# Public fixed walkthrough

The fixed walkthrough at `/projects/proj_demo_2026/decisions` opens without
Google sign-in. Only that exact project ID skips the workspace authentication
screen. Other project IDs retain their existing Google sign-in or configured
connected-demo admission flow. Direct fixed-walkthrough Connections URLs
redirect to Sources.

This change is based on `main` at `40da3e1`. It preserves the newer connected
demo, workspace login, mobile navigation, and sample Google Docs links.
The fixed walkthrough reads bundled snapshots from the running web service;
it does not call the live ingestion or assessment API.

## Production UAT — 18 October 2026

Environment: Next.js 16.4.0 standalone production server on
`http://127.0.0.1:3031`, built with the lockfile dependencies and the deployment's
webpack build. In-app desktop browser; no Google sign-in performed.
`DEMO_PROJECT_ID=proj_connected_uat` was used to exercise the separate connected
demo entry screen without admitting a session or changing its data.

| Check | Result |
| --- | --- |
| Homepage → Explore the fixed walkthrough | Passed: three decisions, one review, two sources; no sign-in prompt. |
| Reviews → evidence → impact graph → production go-live node | Passed: quotes, date delta, graph selection, and four-step path rendered. |
| Access unavailable | Passed: unavailable source details and quote hidden. |
| Evidence unclear / No detected issue | Passed: distinct expected explanations rendered. |
| Sources and Briefs | Passed: two snapshots and the existing demo briefs limitation rendered. |
| Direct fixed-walkthrough Connections URL | Passed: redirected to Sources. |
| Similar project ID with `?demo=true` | Passed: Google sign-in remained required. |
| Configured connected-demo project | Passed: existing Try the connected demo entry screen remained required. |
| Temporary data request failure → Try again | Passed: a local gateway on port 3032 returned one HTTP 503, the app displayed its error, and clicking Try again loaded the real production route's three decisions. No replacement fixture response was supplied on retry. |
| Production route boundaries | Passed: fixture and graph data returned for the exact demo ID; three other IDs returned 404; an unknown scenario returned 400. |

Checks: ESLint, all 12 server tests, production webpack build (including
TypeScript), and `git diff --check` passed. `graphify update .` completed;
generated graph changes remain outside this focused PR.

Limits: mobile viewport interaction, optional external sample Doc access, and
live Google ingestion/extraction/assessment/review writes/Docs export were not
retested. Those flows are unchanged. The full changed path uses the real web
service and its bundled snapshot routes; it needs no live Google service.
The hosted app requires deployment of this change. Local CodeRabbit review
was unavailable because the installed CLI failed signature verification.
