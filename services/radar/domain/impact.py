"""Dependency safety and deterministic projections; no assessment or decision writes."""

from collections import defaultdict, deque
from typing import Annotated, Literal, Sequence, Union

from pydantic import Field

from services.radar.domain.models import (
    Alert, Assumption, Decision, Dependency, Finding, Id, NonEmpty, RadarModel,
)

MAX_EDGES = 500
MAX_PATHS = 1000


class GraphError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class DependencyRequest(RadarModel):
    from_decision_id: Id
    to_decision_id: Id
    relation_type: Literal["enables", "requires_review_of"]
    impact_description: NonEmpty


class DependencyList(RadarModel):
    revision: int = Field(ge=0)
    dependencies: list[Dependency]


class DependencyWrite(RadarModel):
    revision: int = Field(ge=0)
    dependency: Dependency


class FindingNode(RadarModel):
    id: Id
    node_type: Literal["finding"] = "finding"
    impact: Literal["direct_challenge"] = "direct_challenge"
    finding: Finding


class DecisionNode(RadarModel):
    id: Id
    node_type: Literal["decision"] = "decision"
    impact: Literal["direct_challenge", "downstream_impact"]
    decision: Decision


GraphNode = Annotated[Union[FindingNode, DecisionNode], Field(discriminator="node_type")]


class GraphEdge(RadarModel):
    id: Id
    source: Id
    target: Id
    edge_type: Literal["direct_challenge", "dependency"]
    relation_type: Literal["enables", "requires_review_of"] | None = None
    impact_description: str


class AffectedPath(RadarModel):
    decision_id: Id
    node_ids: list[Id]
    edge_ids: list[Id]


class GraphProjection(RadarModel):
    project_id: Id
    alert_id: Id
    revision: int = Field(ge=0)
    root_id: Id
    finding_id: Id
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    affected_paths: list[AffectedPath]


def validate_dag(project_id: str, dependencies: Sequence[Dependency]) -> None:
    """Check the entire stored graph with Kahn's algorithm, including retired nodes."""
    if len(dependencies) > MAX_EDGES:
        raise GraphError("GRAPH_TOO_LARGE", f"A project graph supports at most {MAX_EDGES} edges.")
    incoming: dict[str, int] = defaultdict(int)
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in dependencies:
        if edge.project_id != project_id:
            raise GraphError("CROSS_PROJECT_EDGE", "Dependencies must belong to this project.")
        if edge.from_decision_id == edge.to_decision_id:
            raise GraphError("SELF_DEPENDENCY", "A decision cannot depend on itself.")
        incoming.setdefault(edge.from_decision_id, 0)
        incoming[edge.to_decision_id] += 1
        outgoing[edge.from_decision_id].append(edge.to_decision_id)
    queue = deque(node for node, count in incoming.items() if count == 0)
    visited = 0
    while queue:
        visited += 1
        for target in outgoing[queue.popleft()]:
            incoming[target] -= 1
            if incoming[target] == 0:
                queue.append(target)
    if visited != len(incoming):
        raise GraphError("DEPENDENCY_CYCLE", "This dependency would create a cycle.")


class ImpactService:
    @staticmethod
    def project(
        project_id: str, alert: Alert, finding: Finding, assumption: Assumption,
        decisions: Sequence[Decision], dependencies: Sequence[Dependency], *, revision: int,
    ) -> GraphProjection:
        validate_dag(project_id, dependencies)
        by_id = {row.id: row for row in decisions if row.project_id == project_id}
        root = by_id.get(alert.decision_id)
        if alert.project_id != project_id or finding.project_id != project_id:
            raise GraphError("IMPACT_NOT_FOUND", "Alert or finding not found in this project.", 404)
        if (finding.id != alert.finding_id or finding.classification != "contradicts" or
                finding.assumption_id != assumption.id or assumption.decision_id != alert.decision_id or
                assumption.decision_revision != alert.decision_revision):
            raise GraphError("INVALID_DIRECT_CHALLENGE", "The alert must reference a contradiction on its decision revision.", 409)
        if (root is None or root.status != "active" or assumption.status != "active" or
                root.active_revision != alert.decision_revision):
            raise GraphError("STALE_DIRECT_CHALLENGE", "The challenged decision revision is no longer active.", 409)
        for edge in dependencies:
            if edge.from_decision_id not in by_id or edge.to_decision_id not in by_id:
                raise GraphError("DEPENDENCY_DECISION_MISSING", "A dependency references a missing project decision.", 409)

        # Edges point from the challenged prerequisite to decisions requiring review.
        outgoing: dict[str, list[Dependency]] = defaultdict(list)
        for edge in sorted(dependencies, key=lambda row: row.id):
            if by_id[edge.from_decision_id].status == by_id[edge.to_decision_id].status == "active":
                outgoing[edge.from_decision_id].append(edge)
        direct_edge = GraphEdge(
            id=f"challenge_{finding.id}", source=finding.id, target=root.id,
            edge_type="direct_challenge", impact_description=assumption.statement,
        )
        nodes: list[GraphNode] = [
            FindingNode(id=finding.id, finding=finding),
            DecisionNode(id=root.id, impact="direct_challenge", decision=root),
        ]
        edges = [direct_edge]
        seen_nodes = {root.id}
        seen_edges: set[str] = set()
        paths: list[AffectedPath] = []
        queue = deque([(root.id, [finding.id, root.id], [direct_edge.id])])
        while queue:
            current, node_ids, edge_ids = queue.popleft()
            for edge in outgoing[current]:
                target = edge.to_decision_id
                if len(paths) >= MAX_PATHS:
                    raise GraphError("IMPACT_PATH_LIMIT", f"Projection exceeds {MAX_PATHS} affected paths; narrow the graph.")
                path = AffectedPath(
                    decision_id=target, node_ids=[*node_ids, target], edge_ids=[*edge_ids, edge.id],
                )
                paths.append(path)
                queue.append((target, path.node_ids, path.edge_ids))
                if target not in seen_nodes:
                    seen_nodes.add(target)
                    nodes.append(DecisionNode(id=target, impact="downstream_impact", decision=by_id[target]))
                if edge.id not in seen_edges:
                    seen_edges.add(edge.id)
                    edges.append(GraphEdge(
                        id=edge.id, source=edge.from_decision_id, target=target, edge_type="dependency",
                        relation_type=edge.relation_type, impact_description=edge.impact_description,
                    ))
        return GraphProjection(
            project_id=project_id, alert_id=alert.id, revision=revision, root_id=root.id,
            finding_id=finding.id, nodes=nodes, edges=edges, affected_paths=paths,
        )
