import "server-only";

import vendorDelay from "../../../../../fixtures/vendor-delay.json";
import vendorImpact from "../../../../../fixtures/vendor-delay-impact.json";
import { parseDemoFixture, parseImpactProjection, type EvidenceRef } from "@/lib/domain/models";

/** One validated fixture for the route and future demo reset actions. */
export const demoFixture = parseDemoFixture(vendorDelay);
export const demoImpact = parseImpactProjection(vendorImpact, demoFixture.projectId, demoFixture.alerts[0].id);

const unavailableSourceId = "src_vendor_notes";
const redactedSourceId = "src_unavailable";
const unavailableLabel = "Source access unavailable";
const redactEvidence = (ref: EvidenceRef): EvidenceRef => ref.sourceId === unavailableSourceId
  ? { sourceId: redactedSourceId, sourceTitle: unavailableLabel, nativeUrl: "unavailable", quote: unavailableLabel }
  : ref;

/** Synthetic access-loss case. The response itself omits the unavailable source metadata. */
export const accessUnavailableFixture = parseDemoFixture({
  ...demoFixture,
  sources: demoFixture.sources.map((source) => source.id === unavailableSourceId ? {
    ...source, id: redactedSourceId, name: unavailableLabel,
    mimeType: "application/octet-stream", contentSnapshot: unavailableLabel,
    status: "access_required" as const,
  } : source),
  revisions: demoFixture.revisions.map((row) => ({ ...row, evidence: redactEvidence(row.evidence) })),
  assumptions: demoFixture.assumptions.map((row) => ({ ...row, evidence: redactEvidence(row.evidence) })),
  facts: demoFixture.facts.map((row) => ({
    ...row, sourceId: row.sourceId === unavailableSourceId ? redactedSourceId : row.sourceId,
    evidence: redactEvidence(row.evidence),
  })),
  findings: demoFixture.findings.map((row) => ({
    ...row, baselineEvidence: redactEvidence(row.baselineEvidence),
    updateEvidence: redactEvidence(row.updateEvidence),
  })),
});

export const evidenceUnclearFixture = parseDemoFixture({
  ...accessUnavailableFixture,
  facts: accessUnavailableFixture.facts.filter((row) => row.sourceId !== redactedSourceId),
  findings: [], alerts: [], reviews: [], briefs: [], exports: [],
});

const oldDeliveryQuote = "Due to chip shortage, vendor delivery is pushed back to October 24, 2026.";
const onTimeDeliveryQuote = "Confirmed vendor delivery is scheduled for October 9, 2026.";
export const noDetectedIssueFixture = parseDemoFixture({
  ...demoFixture,
  sources: demoFixture.sources.map((source) => source.id === unavailableSourceId
    ? { ...source, contentSnapshot: source.contentSnapshot.replace(oldDeliveryQuote, onTimeDeliveryQuote) }
    : source),
  facts: demoFixture.facts.map((row) => row.id === "fact_vendor_delivery_24" ? {
    ...row, id: "fact_vendor_delivery_09", value: { type: "date" as const, value: "2026-10-09" },
    evidence: { ...row.evidence, quote: onTimeDeliveryQuote },
  } : row),
  findings: [], alerts: [], reviews: [], briefs: [], exports: [],
});
