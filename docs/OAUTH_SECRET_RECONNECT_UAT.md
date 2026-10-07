# Drive token reconnect UAT

7 October 2026. PR #10 was merged with the current `main` branch for this check.

## Checks completed

- `services/radar/tests/test_connections.py` and `test_secret_manager.py`: 12 passed.
- Web lint, TypeScript, and production build passed.
- Opened the running Sources page as an Auth emulator project administrator. The API used the named `decision-radar` Firestore database and real Secret Manager in `geminimaxxing-509705`.
- Used only `proj_oauth_pr10_uat_20261007` and its synthetic token secret. Opened the in-page disconnect confirmation, cancelled it, and confirmed the connection stayed active. Escape also closed the dialog.
- Pointed that synthetic connection at an invalid secret path. Clicking Disconnect returned HTTP 503 and displayed “The Drive grant could not be removed. Try disconnecting again.” The connection stayed active.
- Restored its valid secret path and retried in the same dialog. The API returned HTTP 204, Sources showed `disconnected`, Firestore removed the secret reference, and Secret Manager reported the synthetic token version `DESTROYED`.

## Remaining merge gate

The synthetic token was not a Google OAuth grant. Connect, disconnect, and reconnect with a real Google Drive account on the named Firestore database, then verify a folder refresh after reconnect. Leave PR #10 open until that live path passes. The isolated local app currently lacks the OAuth client credentials needed to start it.
