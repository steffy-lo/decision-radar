# Project collaboration rules

- Before pushing any change, create and work on a dedicated branch or worktree. Never push project changes directly from `main`.
- Before writing a commit message, use `$mikes-writing-voice` to draft the message. Keep the final message accurate about the changes.
- Before editing a Jira task, use `$mikes-writing-voice` to draft the wording. This applies to issue titles, descriptions, comments, and status updates that include text.
- After every feature implementation, run hands-on UAT in the actual app: click through the changed flow, inspect the rendered result, and report what passed, failed, or could not be tested. Automated tests alone do not satisfy this check. If a feature has no user-facing UI yet, state that limit and test the nearest available integration path.
- If that skill is unavailable, locate it or ask Mike for its source before writing a commit message or editing Jira task text.
- Keep credentials out of this repository and its documentation. Use GitHub's normal sign-in flow for account authorization.
