# Repeat extraction stability — 9 October 2026

The 8 October rehearsal found that re-running Gemini on the same unchanged
`vendor-update.txt` sometimes replaced one verified delivery-date fact with an
unresolved candidate. The next assessment then showed no current alert.

For the MVP, a repeat request now reuses a prior verified extraction only when
the source snapshot, monitored assumption, entity wording, predicate wording,
and published fact records still match. An uncertain result is not cached.
A changed source or mapping runs Gemini again. This keeps a quote-validated
fact stable for the same input while preserving fresh validation when the
evidence changes. A future quality pass should add an explicit reprocess
control if users need to rerun an already verified, unchanged source.

## Checks

- Four focused tests cover the API reuse path, uncertain retry, mapping change,
  changed source, and missing published fact. The extraction and assessment API
  tests passed with them: 25 tests total.
- Cloud Build `6a6cf39f-427f-426c-90ab-afe6191345c4` passed. Private API
  revision `decision-radar-api-staging-00006-n6b` serves the candidate image.
- In the deployed signed-in Sources page, clicked Extract with Gemini for the
  same vendor TXT and trusted Acme Logistics delivery-date wording. The one
  verified October 24 fact remained visible. Its Firestore extraction record
  retained its earlier creation time, showing the result was reused.
- Clicked Run assessment. It completed with one cited nine-day alert and two
  assumptions marked unclear. The impact graph showed the direct challenge,
  two downstream decisions, and the ordered path. Mouse and keyboard node
  selection worked. At 390px, Fit View brought the graph into view.
- Repeated the Drive folder refresh. It completed with seven ready files and
  no duplicate sources. An unavailable folder displayed a recovery message;
  restoring the valid folder returned to the seven-file inventory.
- The fixture fallback displayed access-unavailable, evidence-unclear, and
  no-detected-issue states with explanatory copy.

This was a live stability pass on an existing synthetic project. Its alert had
already been reviewed, so the app did not offer a new review action. It is not
a second complete KAN-26 rehearsal, and KAN-26 stays open. A fresh project is
needed to test a new human review and its audit entry end to end.
