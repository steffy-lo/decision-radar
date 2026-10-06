# KAN-23 quality evaluation, first pass

6 October 2026. `fixtures/kan23_typed_cases.json` has 30 labeled synthetic cases for date, budget, and enum comparisons, including tentative and negated facts, entity and predicate mismatches, a leap day, a year boundary, missing evidence, and an inactive decision. `tests/test_quality_eval.py` builds typed inputs from those labels and checks the assessment output and retained quote references.

The domain run passed all 30 classifications: 5 contradictions, 7 supports, 14 uncertain, and 4 unassessed. It produced 5 expected alerts and no unexpected alerts, giving 100% alert precision and recall **within this synthetic set**. All 12 emitted findings kept quotes contained in their synthetic source text. The test finished in 0.007 seconds on this machine; that is domain execution time, not API or browser latency.

This is an initial gate, not KAN-23 completion. The set has only five positive alerts and does not yet exercise real source permission loss, duplicate ingestion across refreshes, timezone normalization, immutable citation spans, or an authenticated app run. Those need integration cases and a measured browser/API pass before this PR can be merged or the ticket marked done.
