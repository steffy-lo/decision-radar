# Drive token reconnect UAT

7 October 2026. PR #10 was merged with the current `main` branch for this check.

## Checks completed

- `services/radar/tests/test_connections.py` and `test_secret_manager.py`: 12 passed.
- Web lint, TypeScript, and production build passed.
- Opened the running Sources page as an Auth emulator project administrator. The API used the named `decision-radar` Firestore database and real Secret Manager in `geminimaxxing-509705`.
- Used only `proj_oauth_pr10_uat_20261007` and its synthetic token secret. Opened the in-page disconnect confirmation, cancelled it, and confirmed the connection stayed active. Escape also closed the dialog.
- Pointed that synthetic connection at an invalid secret path. Clicking Disconnect returned HTTP 503 and displayed “The Drive grant could not be removed. Try disconnecting again.” The connection stayed active.
- Restored its valid secret path and retried in the same dialog. The API returned HTTP 204, Sources showed `disconnected`, Firestore removed the secret reference, and Secret Manager reported the synthetic token version `DESTROYED`.

## Live Google Drive pass, 8 October 2026

- Used a separate localhost OAuth client with Drive read-only access. Its credential stayed outside the repository. The browser used the Auth emulator for project sign-in; Google OAuth, Drive, Firestore, and Secret Manager were live services.
- Connected Mike's Google account from the running Sources page. Refreshed the private synthetic Drive folder. The app scanned five files: a decision Google Doc, a Meet transcript Google Doc, two text files, and a Google Doc in a subfolder. Firestore saved five source snapshots with content.
- Disconnected in the app. Sources showed `disconnected`, Firestore removed the secret reference, and both existing Secret Manager token versions were `DESTROYED`. The five source snapshots remained available for review.
- Reconnected the same Google account through the app. Refreshed the same folder again: five scanned, five unchanged, no errors. Firestore showed an active connection with a secret reference; Secret Manager had one `ENABLED` version and the two prior versions remained `DESTROYED`.

This passes the PR's real connect, disconnect, reconnect, and folder-refresh path. It does not test production Firebase sign-in or deployed browser routing; those remain separate deployment checks.
