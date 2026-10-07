import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import ts from "../apps/web/node_modules/typescript/lib/typescript.js";

async function loadModule(path) {
  const source = readFileSync(new URL(path, import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  return import(`data:text/javascript,${encodeURIComponent(compiled)}`);
}
const { parseImpactProjection } = await loadModule("../apps/web/src/lib/domain/models.ts");
const { impactPositions, pathsForNode, evidenceUrl, edgeLabel, impactValue } = await loadModule("../apps/web/src/lib/domain/impact-view.ts");
const fixture = JSON.parse(readFileSync(new URL("../fixtures/vendor-delay-impact.json", import.meta.url), "utf8"));
const parse = (value) => parseImpactProjection(value, fixture.projectId, fixture.alertId);
const changed = (edit) => { const value = structuredClone(fixture); edit(value); return value; };

test("the UI preserves server paths and has no direct evidence on downstream nodes", () => {
  const graph = parse(fixture);
  assert.deepEqual(pathsForNode(graph, "dec_production_go_live"), [graph.affectedPaths[1]]);
  assert.deepEqual(pathsForNode(graph, graph.rootId)[0].edgeIds, [graph.edges[0].id]);
  assert.equal(graph.nodes[2].finding, undefined);
  assert.equal(edgeLabel(graph.edges[1]), "Enables");
  assert.equal(impactPositions(graph).get("dec_production_go_live").y, 720);
});

test("diamond paths remain separately selectable with shared nodes", () => {
  const value = changed((graph) => {
    graph.edges.push({ id: "dep_shortcut", source: graph.rootId, target: "dec_production_go_live", edgeType: "dependency", relationType: "requires_review_of", impactDescription: "Review release readiness." });
    graph.affectedPaths.push({ decisionId: "dec_production_go_live", nodeIds: [graph.findingId, graph.rootId, "dec_production_go_live"], edgeIds: [graph.edges[0].id, "dep_shortcut"] });
  });
  const graph = parse(value);
  assert.equal(pathsForNode(graph, "dec_production_go_live").length, 2);
  assert.equal(graph.nodes.length, 4);
  assert.equal(impactPositions(graph).get("dec_production_go_live").y, 720);
});

test("malformed scope, direct challenge and disconnected or incomplete paths fail closed", () => {
  for (const edit of [
    (g) => { g.projectId = "proj_other"; },
    (g) => { g.nodes[1].decision.projectId = "proj_other"; },
    (g) => { g.nodes[0].finding.classification = "supports"; },
    (g) => { g.nodes[2].impact = "direct_challenge"; },
    (g) => { g.nodes[1].decision.status = "retired"; },
    (g) => { g.edges[0].relationType = "enables"; },
    (g) => { g.edges[1].target = "dec_missing"; },
    (g) => { g.affectedPaths[1].edgeIds.reverse(); },
    (g) => { g.affectedPaths.pop(); },
    (g) => { delete g.nodes[0].finding.updateEvidence; },
    (g) => { g.nodes.push(g.nodes[1]); },
  ]) assert.throws(() => parse(changed(edit)));
});

test("evidence links reject executable protocols and typed values keep units", () => {
  assert.equal(evidenceUrl("javascript:alert(1)"), null);
  assert.equal(evidenceUrl("data:text/html,test"), null);
  assert.equal(evidenceUrl("not a URL"), null);
  assert.equal(evidenceUrl("https://docs.google.com/document/d/example"), "https://docs.google.com/document/d/example");
  assert.equal(impactValue({ type: "decimal", value: "1200.50", unit: "USD" }), "1200.50 USD");
});
