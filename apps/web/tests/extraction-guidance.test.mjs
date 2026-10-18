import assert from "node:assert/strict";
import { test } from "node:test";
import { extractionBlocker, extractionHelp } from "../src/lib/domain/extraction-guidance.ts";

const ready = { loading: false, role: "editor", assumption: true, source: { status: "ready" }, subject: "Acme Logistics", detail: "delivery date", busy: false };

test("readiness tells the user the next missing step", () => {
  assert.match(extractionBlocker({ ...ready, assumption: false, source: undefined, subject: "" }), /Choose a requirement/);
  assert.match(extractionBlocker({ ...ready, source: undefined, subject: "" }), /Choose the document/);
  assert.match(extractionBlocker({ ...ready, subject: "  " }), /Enter who or what/);
  assert.match(extractionBlocker({ ...ready, detail: " " }), /information to look for/);
  assert.equal(extractionBlocker(ready), null);
});

test("unavailable access and sources cannot appear ready even with complete matching phrases", () => {
  for (const role of ["admin", "editor"]) assert.equal(extractionBlocker({ ...ready, role }), null);
  assert.match(extractionBlocker({ ...ready, role: "viewer" }), /view-only/);
  assert.match(extractionBlocker({ ...ready, role: undefined }), /access could not be checked/);
  assert.match(extractionBlocker({ ...ready, source: { status: "ready", monitoring_paused: true } }), /Resume it in Connections/);
  assert.match(extractionBlocker({ ...ready, source: { status: "failed" } }), /Refresh Drive/);
  assert.match(extractionBlocker({ ...ready, busy: true }), /Gemini is reading/);
});

test("validation failures have actionable plain language without exposing raw reasons", () => {
  assert.match(extractionHelp("entity is unresolved"), /Check the name/);
  assert.match(extractionHelp("predicate is unresolved"), /Check your description/);
  assert.match(extractionHelp("typed value is not visible in evidence quote"), /including the year/);
  assert.match(extractionHelp("source wording is tentative"), /possibility/);
  assert.match(extractionHelp("source wording may be negated"), /Clarify the wording/);
  assert.match(extractionHelp("source context is incomplete"), /missing details/);
  assert.match(extractionHelp("new internal failure code"), /could not be verified/);
});
