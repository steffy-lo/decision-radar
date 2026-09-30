# KAN-4, KAN-16, and KAN-17 integration UAT

This branch connects the MVP path in one project workspace: refresh a Drive folder, create and confirm a quote-backed decision, extract verified facts with Vertex Gemini, then run a deterministic assessment and inspect its alert.

## Local UAT flow

1. Sign in to a project workspace and open **Sources**.
2. Connect Drive and enter the ID of a folder containing a Google Doc or text file. Click **Refresh folder**. The source list should show the file; a second refresh should report it unchanged.
3. Open **Decisions**. Select a source, paste an exact quote from its displayed text, enter a decision and date assumption, then click **Create draft** and **Confirm decision**.
4. Return to **Sources**. Select the monitored assumption and enter the entity and predicate wording used in the source. Click **Extract with Gemini**. Check the returned quote and whether each fact is ready or uncertain. Only ready confirmed facts are published for assessment.
5. Open **Reviews** and click **Run assessment**. A later confirmed date should create a review alert with the original assumption quote, new source quote, and day difference. Repeating the run should not duplicate the alert.

The local synthetic UAT environment uses Firebase emulators and a test Drive gateway. It does not test Google's OAuth consent screen or read a real Drive folder. The Gemini extraction in this run used Vertex AI in GCP project `geminimaxxing-509705`; no production Firestore records were written. A real Drive/OAuth pass remains after KAN-3 is merged and its OAuth configuration is available.

Keep credentials in local environment configuration or Google Application Default Credentials, never in this repository.
