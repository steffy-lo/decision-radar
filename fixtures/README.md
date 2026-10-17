# Deterministic vendor-delay fixture

[vendor-delay.json](vendor-delay.json) is the shared KAN-14 contract fixture for the FastAPI domain layer and the Next.js UI. It is synthetic. Its source links open real, read-only Google Docs containing the same sample text:

- [Product Launch PRD v1](https://docs.google.com/document/d/1zETnMb2gHERIL2xPshdMhgVhSqTmimVjT5tv2HX8Vq0/edit)
- [Vendor Sync & Status Notes](https://docs.google.com/document/d/1hCXUFL1AOpCs0ItgUBBPzk87qGu2IaPuC6dZk6QPRfg/edit)

Reviews, Sources and the impact graph use these links. The Docs are reference copies for the public demo, not a live Drive ingestion connection: assessments still use the bundled `contentSnapshot`, and editing a sample Doc does not update a fixture result. Keep the cited text in the Docs aligned with these snapshots; the built-in example remains 10 October → 24 October (14 days), distinct from the connected staging rehearsal's nine-day scenario.

The launch decision is dated 20 October 2026 and assumes vendor delivery by 10 October. A confirmed update moves delivery to 24 October. The fixture carries both exact source quotes, the 14-calendar-day contradiction, and dependency edges from launch readiness through integration testing to production go-live. It also includes a supported decimal budget fact, a tentative date, and a negated enum fact for extraction and validation examples.

The older KAN-14 ticket describes a Sheet update. The newer [MVP contract](../docs/LLD_MVP.md) and [Confluence MVP scope](https://geminimaxxing.atlassian.net/wiki/spaces/GeminiMaxx/pages/163960/MVP+Scope+Delivery+Plan+Backlog) narrow intake to Google Docs and TXT, so this fixture represents the update as a vendor notes Doc. A Sheets adapter can reuse the same typed fact and finding later.

Validation:

```sh
services/radar/.venv/bin/python -m unittest discover -s tests -p 'test_contract.py'
node --test tests/test_contract.mjs
```

The TypeScript test uses the repository's installed TypeScript compiler, so run `npm ci` in `apps/web` first.
