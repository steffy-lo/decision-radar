# Project collaboration rules

- Before pushing any change, create and work on a dedicated branch or worktree. Never push project changes directly from `main`.
- Draft commit messages and Jira wording in a direct, practical voice. State what changed or what needs doing in plain language, keep technical details exact, and avoid promotional wording. Jira titles, descriptions, comments, and written status updates follow this rule.
- After every feature implementation, run hands-on UAT in the actual app: click through the changed flow, inspect the rendered result, and report what passed, failed, or could not be tested. Automated tests alone do not satisfy this check. If a feature has no user-facing UI yet, state that limit and test the nearest available integration path.
- Before merging a feature PR, test its full path in the running app against the real service and resulting data. Include relevant failure and retry states. Unit tests and fixture-only UAT support this check but do not replace it. Record the environment and limits in the PR, leave the PR open if the full path cannot be verified, and rerun the integrated flow after dependency merges.
- Keep credentials out of this repository and its documentation. Use GitHub's normal sign-in flow for account authorization.

## Current delivery sequence

- KAN-3 (Google OAuth) enables KAN-4 (single-folder Drive ingestion). KAN-4 supplies source snapshots for KAN-16 (Gemini extraction), which supplies validated facts to KAN-17 (typed assessment and decision confirmation).
- Keep KAN-4, KAN-16, and KAN-17 in one implementation and test track. Run the full flow against the KAN-3 connection after KAN-3 is merged; verify the Doc, TXT, nested Doc, and saved Meet transcript paths called for in KAN-4.
- Prefer focused PRs based on the current `main`. Avoid new stacked PRs where practical, since review changes can drift between branches. When a dependency makes a stack necessary, state the base and integration order, then rebase and retest after the prerequisite merges. The existing KAN-16 and KAN-17 draft PRs need this integration check.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
