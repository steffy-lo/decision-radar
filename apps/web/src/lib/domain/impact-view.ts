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

/** Native links accept only web URLs; malformed evidence never becomes executable. */
export function evidenceUrl(value: string): string | null {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}
