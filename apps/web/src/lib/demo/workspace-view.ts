import { evidenceUrl } from "@/lib/domain/impact-view";
import type { Alert, Assumption, Decision, DemoFixture, Dependency, Finding } from "@/lib/domain/models";

export type DecisionView = {
  decision: Decision;
  assumptions: Assumption[];
  dateAssumption: Assumption | undefined;
  openAlert: Alert | undefined;
  finding: Finding | undefined;
};

export type ReviewView = {
  alert: Alert;
  decision: Decision;
  finding: Finding;
  dependencies: Dependency[];
};

export function createWorkspaceView(data: DemoFixture) {
  const assumptionsByDecision = new Map<string, Assumption[]>();
  const dependenciesByDecision = new Map<string, Dependency[]>();
  const openAlertsByDecision = new Map<string, Alert>();
  const findingsById = new Map(data.findings.map((finding) => [finding.id, finding]));
  const decisionsById = new Map(data.decisions.map((decision) => [decision.id, decision]));

  for (const assumption of data.assumptions) {
    const related = assumptionsByDecision.get(assumption.decisionId) ?? [];
    related.push(assumption);
    assumptionsByDecision.set(assumption.decisionId, related);
  }
  for (const dependency of data.dependencies) {
    const related = dependenciesByDecision.get(dependency.fromDecisionId) ?? [];
    related.push(dependency);
    dependenciesByDecision.set(dependency.fromDecisionId, related);
  }
  for (const alert of data.alerts) {
    if (alert.reviewState === "open" && !openAlertsByDecision.has(alert.decisionId)) {
      openAlertsByDecision.set(alert.decisionId, alert);
    }
  }

  const decisions: DecisionView[] = data.decisions.map((decision) => {
    const assumptions = assumptionsByDecision.get(decision.id) ?? [];
    const openAlert = openAlertsByDecision.get(decision.id);
    return {
      decision,
      assumptions,
      dateAssumption: assumptions.find((item) => item.expectedValue.type === "date"),
      openAlert,
      finding: openAlert ? findingsById.get(openAlert.findingId) : undefined,
    };
  });
  const openReviews: ReviewView[] = data.alerts.flatMap((alert) => {
    if (alert.reviewState !== "open") return [];
    const decision = decisionsById.get(alert.decisionId);
    const finding = findingsById.get(alert.findingId);
    return decision && finding ? [{ alert, decision, finding, dependencies: dependenciesByDecision.get(decision.id) ?? [] }] : [];
  });

  const sourceEvidence = [
    ...data.revisions.map((row) => row.evidence),
    ...data.assumptions.map((row) => row.evidence),
    ...data.facts.map((row) => row.evidence),
    ...data.findings.flatMap((row) => [row.baselineEvidence, row.updateEvidence]),
  ];
  const sources = data.sources.map((source) => ({
    ...source,
    nativeUrl: source.status === "ready"
      ? evidenceUrl(sourceEvidence.find((ref) => ref.sourceId === source.id)?.nativeUrl ?? "")
      : null,
  }));

  return { decisions, openReviews, sources };
}
