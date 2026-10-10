import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import ts from "../apps/web/node_modules/typescript/lib/typescript.js";

const fixture = JSON.parse(readFileSync(new URL("../fixtures/vendor-delay.json", import.meta.url), "utf8"));
const source = readFileSync(new URL("../apps/web/src/lib/domain/models.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const { parseDemoFixture } = await import(`data:text/javascript,${encodeURIComponent(compiled)}`);
const changed = (edit) => {
  const copy = structuredClone(fixture);
  edit(copy);
  return copy;
};

test("the shared fixture validates with its evidence and downstream path", () => {
  const demo = parseDemoFixture(fixture);
  assert.equal(demo.findings[0].deltaDays, 14);
  assert.equal(demo.alerts[0].id, "alt_delivery_delayed");
  assert.deepEqual(demo.dependencies.map((edge) => edge.toDecisionId), [
    "dec_integration_testing", "dec_production_go_live",
  ]);
  assert.deepEqual(new Set(demo.facts.map((fact) => fact.modality)),
    new Set(["confirmed", "tentative", "negated"]));
  assert.equal(demo.assumptions[1].expectedValue.type, "decimal");
});

test("malformed IDs and missing evidence are rejected", () => {
  assert.throws(() => parseDemoFixture(changed((p) => { p.decisions[0].id = "../bad"; })));
  assert.throws(() => parseDemoFixture(changed((p) => { delete p.findings[0].updateEvidence; })));
  assert.throws(() => parseDemoFixture(changed((p) => { p.findings[0].updateEvidence.quote = "unverified quote"; })));
});

test("versioned historical evidence can outlive the current source text", () => {
  const copy = changed((p) => {
    const ref = p.revisions[0].evidence;
    ref.sourceVersionId = "ver_abc123";
    ref.spanId = "span_abc123";
    ref.quote = "A quote retained only in the prior version.";
  });
  assert.doesNotThrow(() => parseDemoFixture(copy));
  assert.throws(() => parseDemoFixture(changed((p) => {
    p.revisions[0].evidence.sourceVersionId = "ver_abc123";
  })));
});

test("invalid typed values, modality, and date deltas are rejected", () => {
  assert.throws(() => parseDemoFixture(changed((p) => { p.assumptions[0].expectedValue.value = "2026-02-30"; })));
  assert.throws(() => parseDemoFixture(changed((p) => { p.assumptions[1].expectedValue.value = "not a decimal"; })));
  assert.throws(() => parseDemoFixture(changed((p) => { p.facts[3].value.value = ""; })));
  assert.throws(() => parseDemoFixture(changed((p) => { p.facts[0].modality = "maybe"; })));
  assert.throws(() => parseDemoFixture(changed((p) => { p.findings[0].deltaDays = 13; })));
});
