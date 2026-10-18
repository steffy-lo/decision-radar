import assert from "node:assert/strict";
import { test } from "node:test";
import { assessmentStatus } from "../src/lib/domain/assessment-status.ts";

test("a completed empty run never claims the documents agree", () => {
  assert.equal(assessmentStatus({ findingCount: 0, coverage: [] }, 0).title, "Nothing was assessed");
});

test("partial and unavailable coverage cannot appear as a clean result", () => {
  assert.equal(assessmentStatus({ findingCount: 0, coverage: [{ state: "unassessed" }] }, 0).title, "Evidence unclear");
  assert.equal(assessmentStatus({ findingCount: 1, coverage: [{ state: "assessed" }] }, 0, true).title, "Evidence unclear");
});

test("results distinguish an alert from comparisons that found no conflict", () => {
  const run = { findingCount: 1, coverage: [{ state: "assessed" }] };
  assert.equal(assessmentStatus(run, 1).title, "Decisions need review");
  assert.equal(assessmentStatus(run, 0).title, "No conflict in the comparisons made");
});
