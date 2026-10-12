import type { ImpactEdge, ImpactNode, ImpactPath, ImpactProjection, TypedValue } from "./models";

export function impactTitle(node: ImpactNode): string {
  if (node.nodeType === "decision") return node.decision.statement;
  return node.finding.projectId === "proj_demo_2026" && node.id === "fnd_delivery_delayed" ? "Vendor delivery delayed" : "New evidence challenges an assumption";
}

export function impactValue(value: TypedValue): string {
  return value.type === "decimal" ? `${value.value} ${value.unit}` : String(value.value);
}

export function edgeLabel(edge: ImpactEdge): string {
  return edge.edgeType === "direct_challenge" ? "Challenges" : edge.relationType === "enables" ? "Enables" : "Requires review";
}

/** Presentation coordinates only; never add edges or calculate dependency paths. */
export function impactPositions(graph: ImpactProjection): Map<string, { x: number; y: number }> {
  const levels = new Map([[graph.findingId, 0], [graph.rootId, 1]]);
  for (const path of graph.affectedPaths) {
    path.nodeIds.forEach((id, index) => levels.set(id, Math.max(levels.get(id) ?? 0, index)));
  }
  const rows = new Map<number, number>();
  return new Map(graph.nodes.map((node) => {
    const level = levels.get(node.id) ?? 0;
    const row = rows.get(level) ?? 0;
    rows.set(level, row + 1);
    return [node.id, { x: row * 310, y: level * 240 }];
  }));
}

export function pathsForNode(graph: ImpactProjection, nodeId: string): ImpactPath[] {
  if (nodeId === graph.findingId) return [{ decisionId: nodeId, nodeIds: [nodeId], edgeIds: [] }];
  if (nodeId === graph.rootId) {
    const edge = graph.edges.find((edge) => edge.edgeType === "direct_challenge")!;
    return [{ decisionId: nodeId, nodeIds: [edge.source, edge.target], edgeIds: [edge.id] }];
  }
  return graph.affectedPaths.filter((path) => path.decisionId === nodeId);
}

export type ImpactExplanation = {
  summary: string;
  evidenceBasis: string;
  reviewReason: string;
  briefText: string;
};

/** Keep the narrative tied to the server's ordered path and recorded edge reasons. */
export function explainImpactPath(graph: ImpactProjection, nodeId: string, path: ImpactPath): ImpactExplanation {
  const selected = graph.nodes.find((node) => node.id === nodeId);
  const root = graph.nodes.find((node) => node.id === graph.rootId);
  const trigger = graph.nodes.find((node) => node.id === graph.findingId);
  if (!selected || root?.nodeType !== "decision" || trigger?.nodeType !== "finding" ||
      path.nodeIds.at(-1) !== nodeId) throw new Error("The selected impact path is unavailable.");

  const change = `${impactValue(trigger.finding.baselineValue)} → ${impactValue(trigger.finding.extractedValue)}`;
  const delta = trigger.finding.deltaDays === null ? "" :
    ` (${trigger.finding.deltaDays > 0 ? "+" : ""}${trigger.finding.deltaDays} days)`;
  const direct = selected.nodeType === "finding" || selected.id === graph.rootId;
  const steps = path.edgeIds.slice(1).map((edgeId) => {
    const edge = graph.edges.find((row) => row.id === edgeId);
    const target = graph.nodes.find((node) => node.id === edge?.target);
    if (!edge || target?.nodeType !== "decision") throw new Error("The recorded impact path is incomplete.");
    const relationship = edge.relationType === "enables" ? "enables" : "requires review of";
    return `${relationship} ${target.decision.statement}: ${edge.impactDescription}`;
  });
  const summary = selected.nodeType === "finding"
    ? `The evidence changed from ${change}${delta} and challenges the assumption behind ${root.decision.statement}.`
    : selected.id === graph.rootId
      ? `${selected.decision.statement} is directly challenged by the change from ${change}${delta}.`
      : `${selected.decision.statement} is downstream of ${root.decision.statement} through ${steps.length} recorded ${steps.length === 1 ? "relationship" : "relationships"}.`;
  const evidenceBasis = direct
    ? `Direct evidence: “${trigger.finding.baselineEvidence.quote}” → “${trigger.finding.updateEvidence.quote}”.`
    : `Projected impact from recorded dependencies. The trigger has cited evidence; this decision has no separate contradiction evidence.`;
  const reviewReason = direct
    ? `Review the changed assumption before relying on ${root.decision.statement}.`
    : `Review each recorded dependency before changing this decision. The graph does not claim that this decision's own evidence changed.`;
  const briefText = [
    `Impact: ${impactTitle(selected)}`,
    summary,
    `Evidence basis: ${evidenceBasis}`,
    ...steps.map((step, index) => `Path ${index + 1}: ${step}`),
    `Why review: ${reviewReason}`,
    `Original source: ${trigger.finding.baselineEvidence.sourceTitle} — ${trigger.finding.baselineEvidence.quote}${evidenceUrl(trigger.finding.baselineEvidence.nativeUrl) ? ` (${evidenceUrl(trigger.finding.baselineEvidence.nativeUrl)})` : ""}`,
    `Update source: ${trigger.finding.updateEvidence.sourceTitle} — ${trigger.finding.updateEvidence.quote}${evidenceUrl(trigger.finding.updateEvidence.nativeUrl) ? ` (${evidenceUrl(trigger.finding.updateEvidence.nativeUrl)})` : ""}`,
  ].join("\n");
  return { summary, evidenceBasis, reviewReason, briefText };
}

/** Native links accept only web URLs; malformed evidence never becomes executable. */
export function evidenceUrl(value: string): string | null {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}
