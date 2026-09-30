# KAN-4 PR integration check

30 September 2026. This branch merges the current `main` after KAN-3 PR #7 and adds the existing KAN-4 UI integration commit.

## Checks

- Python suite: 25 passed and 4 subtests passed.
- Shared contract tests: 3 passed.
- Next.js Webpack production build: passed after using the route's `projectId` in the refresh action.
- Browser UAT at `http://localhost:3006/projects/proj_kan4_uat/sources`: signed in through the local Firebase Auth emulator, opened Sources, entered a synthetic folder ID, clicked **Refresh folder**, and saw one new connected source. A reload retained the selected folder. The live page no longer shows the unrelated prototype fixture error.

The browser pass used a localhost synthetic gateway for membership, connection, and refresh responses. It verifies the app control and project routing, not a new Drive API call. A previous integrated-branch UAT completed the real Google OAuth, five-file Drive refresh, Secret Manager token retrieval, and Vertex flow with a synthetic Drive folder; see `docs/KAN3_4_16_17_REAL_DRIVE_UAT.md` in `codex/kan3-4-16-17-real-drive-e2e`. The Cloud Run service cannot complete this flow yet: project IAM grants for its runtime identity are absent, and Google Cloud currently has no Firestore database.
