"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { Background, Controls, Handle, MarkerType, Position, ReactFlow,
  type Node, type NodeProps } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { fetchPrivateApi } from "@/lib/api/client";
import { isDemoProject } from "@/lib/demo/use-project-data";
import { parseImpactProjection, type EvidenceRef, type ImpactNode, type ImpactProjection } from "@/lib/domain/models";
import { edgeLabel, evidenceUrl, impactPositions, impactTitle, impactValue, pathsForNode } from "@/lib/domain/impact-view";
import styles from "./impact-graph.module.css";

type FlowNode = Node<{ record: ImpactNode }, "impact">;

function category(node: ImpactNode): string {
  return node.nodeType === "finding" ? "Evidence trigger" : node.impact === "direct_challenge" ? "Challenged decision" : "Downstream effect";
}

function ImpactCard({ data, selected }: NodeProps<FlowNode>) {
  const node = data.record;
  return <div className={`${styles.node} ${node.nodeType === "finding" ? styles.trigger : node.impact === "direct_challenge" ? styles.challenged : styles.downstream} ${selected ? styles.selected : ""}`}>
    {node.nodeType === "decision" && <Handle type="target" position={Position.Top} isConnectable={false} />}
    <span className={styles.category}>{category(node)}</span>
    <strong>{impactTitle(node)}</strong>
    {node.nodeType === "finding" ? <>
      <span>{impactValue(node.finding.baselineValue)} → {impactValue(node.finding.extractedValue)}</span>
      {node.finding.deltaDays !== null && <b className={styles.delta}>{node.finding.deltaDays > 0 ? "+" : ""}{node.finding.deltaDays} days</b>}
    </> : <span>{node.decision.owner}</span>}
    <small>{node.nodeType === "finding" || node.impact === "direct_challenge" ? "Direct evidence available" : "Dependency rationale · trigger evidence available"}</small>
    <Handle type="source" position={Position.Bottom} isConnectable={false} />
  </div>;
}
const nodeTypes = { impact: ImpactCard };

function Evidence({ label, evidence, demo }: { label: string; evidence: EvidenceRef; demo: boolean }) {
  const url = evidenceUrl(evidence.nativeUrl);
  return <section className={styles.evidence}>
    <h4>{label}</h4><blockquote>“{evidence.quote}”</blockquote><p>{evidence.sourceTitle}</p>
    {demo ? <small>Synthetic source · quote shown above</small> : url ?
      <a href={url} target="_blank" rel="noopener noreferrer">Open source ↗</a> : <small>Source link unavailable</small>}
  </section>;
}

function GraphView({ graph, demo }: { graph: ImpactProjection; demo: boolean }) {
  const canvas = useRef<HTMLDivElement>(null);
  const [layoutVersion, setLayoutVersion] = useState(0);
  useEffect(() => {
    if (!canvas.current) return;
    let previous: { width: number; height: number } | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      if (previous && (Math.abs(width - previous.width) > 1 || Math.abs(height - previous.height) > 1)) {
        clearTimeout(timer);
        timer = setTimeout(() => setLayoutVersion((value) => value + 1), 100);
      }
      previous = { width, height };
    });
    observer.observe(canvas.current);
    return () => { observer.disconnect(); clearTimeout(timer); };
  }, []);
  const [selectedId, setSelectedId] = useState(graph.findingId);
  const [pathIndex, setPathIndex] = useState(0);
  const detailId = useId();
  const pathSelectId = useId();
  const selected = graph.nodes.find((node) => node.id === selectedId)!;
  const paths = useMemo(() => pathsForNode(graph, selectedId), [graph, selectedId]);
  const path = paths[pathIndex] ?? paths[0];
  const positions = useMemo(() => impactPositions(graph), [graph]);
  const select = useCallback((id: string) => { setSelectedId(id); setPathIndex(0); }, []);
  const nodes: FlowNode[] = useMemo(() => graph.nodes.map((node) => ({
    id: node.id, type: "impact", data: { record: node }, position: positions.get(node.id)!,
    selected: node.id === selectedId, ariaRole: "button", ariaLabel: `${category(node)}: ${impactTitle(node)}`,
    domAttributes: { "aria-controls": detailId, "aria-pressed": node.id === selectedId },
  })), [graph, positions, selectedId, detailId]);
  const edges = useMemo(() => graph.edges.map((edge) => {
    const active = path?.edgeIds.includes(edge.id);
    const color = edge.edgeType === "direct_challenge" ? "#b76c17" : active ? "#197baf" : "#94a5b5";
    return { id: edge.id, source: edge.source, target: edge.target, type: "smoothstep",
      label: edgeLabel(edge), ariaLabel: `${edgeLabel(edge)}: ${edge.impactDescription}`,
      markerEnd: { type: MarkerType.ArrowClosed, color },
      style: { stroke: color, strokeWidth: active ? 3 : 1.5 }, labelStyle: { fill: "#34414d", fontSize: 12 },
      labelBgStyle: { fill: "#f6f8fa" }, labelBgPadding: [7, 4] as [number, number],
    };
  }), [graph, path]);
  const trigger = graph.nodes.find((node) => node.nodeType === "finding")!;
  const finding = trigger.nodeType === "finding" ? trigger.finding : null;
  return <section className={styles.workspace} aria-label="Decision impact graph">
    <div className={styles.header}><div><span className="eyebrow">IMPACT MAP</span><h2>Follow the ripple</h2></div>
      <span>{graph.nodes.length - 2} downstream {graph.nodes.length === 3 ? "decision" : "decisions"}</span></div>
    <div className={styles.legend}><span className={styles.triggerKey}>Evidence trigger</span><span className={styles.challengeKey}>Direct challenge</span><span className={styles.downstreamKey}>Downstream effect</span></div>
    <p className={styles.help}>Drag the background to pan. Use + / − to zoom. Tab to a node and press Enter or Space to inspect it.</p>
    <div className={styles.layout}>
      <div className={styles.canvas} ref={canvas}>
        <ReactFlow<FlowNode> key={layoutVersion} nodes={nodes} edges={edges} nodeTypes={nodeTypes}
          nodesDraggable={false} nodesConnectable={false} edgesReconnectable={false} deleteKeyCode={null}
          nodesFocusable edgesFocusable autoPanOnNodeFocus fitView fitViewOptions={{ padding: 0.2 }} minZoom={0.25} maxZoom={1.5}
          onNodeClick={(_event, node) => select(node.id)}
          onNodesChange={(changes) => { for (const change of changes) if (change.type === "select" && change.selected) select(change.id); }}
          ariaLabelConfig={{ "node.a11yDescription.default": "Press Enter or Space to inspect this node. Tab moves to the next node.",
            "edge.a11yDescription.default": "This relationship is read only. Its rationale is in the ordered impact path." }}>
          <Background gap={20} color="#d8e2e9" /><Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <aside className={styles.detail} id={detailId} aria-label="Selected impact details">
        <p className="sr-only" role="status">Selected {category(selected)}: {impactTitle(selected)}</p>
        <span className={styles.category}>{category(selected)}</span><h3>{impactTitle(selected)}</h3>
        {selected.nodeType === "decision" && <><p className={styles.owner}>Owner: {selected.decision.owner}</p><p>{selected.decision.rationale}</p></>}
        <h4>Ordered impact path</h4>
        {paths.length > 1 && <><label htmlFor={pathSelectId}>Path to this decision</label><select id={pathSelectId} value={pathIndex} onChange={(event) => setPathIndex(Number(event.target.value))}>
          {paths.map((item, index) => <option key={item.edgeIds.join("_")} value={index}>Path {index + 1} of {paths.length} · {item.edgeIds.length} steps</option>)}
        </select></>}
        <ol className={styles.path}>{path?.nodeIds.map((id, index) => {
          const node = graph.nodes.find((node) => node.id === id)!;
          const edge = index > 0 ? graph.edges.find((edge) => edge.id === path.edgeIds[index - 1]) : undefined;
          return <li key={id}>{edge && <div className={styles.relationship}><b>{edgeLabel(edge)}</b><p>{edge.impactDescription}</p></div>}
            <button type="button" onClick={() => select(id)} aria-pressed={id === selectedId}>{index + 1}. {impactTitle(node)}</button></li>;
        })}</ol>
        {selected.impact === "downstream_impact" ? <div className={styles.coverage}>
          <h4>Evidence availability</h4><p>This decision is affected through a recorded dependency. No direct contradiction evidence is attached to this node.</p>
          <button className="button button--secondary" type="button" onClick={() => select(graph.findingId)}>Inspect trigger evidence</button>
        </div> : finding && <>
          {selected.nodeType === "decision" && <p className={styles.coverage}>Challenged assumption: {graph.edges.find((edge) => edge.edgeType === "direct_challenge")?.impactDescription}</p>}
          <h4>Supporting evidence</h4>
          <p>Expected: <strong>{impactValue(finding.baselineValue)}</strong> · Updated: <strong>{impactValue(finding.extractedValue)}</strong>{finding.deltaDays !== null && <> · <strong>{finding.deltaDays > 0 ? "+" : ""}{finding.deltaDays} days</strong></>}</p>
          <Evidence label="Original assumption" evidence={finding.baselineEvidence} demo={demo} />
          <Evidence label="New evidence" evidence={finding.updateEvidence} demo={demo} />
        </>}
      </aside>
    </div>
    <nav className={styles.nodeList} aria-label="Inspect graph nodes">{graph.nodes.map((node) => <button key={node.id} type="button" aria-pressed={node.id === selectedId} onClick={() => select(node.id)}>{impactTitle(node)}</button>)}</nav>
  </section>;
}

export function ImpactGraph({ projectId, alertId }: { projectId: string; alertId: string }) {
  const [state, setState] = useState<{ key: string; graph?: ImpactProjection; error?: string }>();
  const [attempt, setAttempt] = useState(0);
  const key = `${projectId}/${alertId}`;
  const demo = isDemoProject(projectId);
  useEffect(() => {
    const controller = new AbortController();
    const base = `/api/v1/projects/${encodeURIComponent(projectId)}`;
    const url = `${base}${demo ? "/fixture" : ""}/alerts/${encodeURIComponent(alertId)}/graph`;
    const request = demo ? fetch(url, { cache: "no-store", signal: controller.signal }) : fetchPrivateApi(url, { signal: controller.signal });
    request.then(async (response) => {
      if (!response.ok) throw new Error(response.status === 409 ? "This review has changed. Reload the current review before inspecting its impact." :
        response.status === 403 ? "You do not have access to this project’s impact graph." :
        response.status === 404 ? "This impact graph could not be found." : "The impact graph could not be loaded. Try again.");
      return parseImpactProjection(await response.json(), projectId, alertId);
    }).then((graph) => { if (!controller.signal.aborted) setState({ key, graph }); })
      .catch((error: unknown) => { if (!controller.signal.aborted) setState({ key, error: error instanceof Error ? error.message : "The impact graph could not be loaded." }); });
    return () => controller.abort();
  }, [projectId, alertId, demo, key, attempt]);
  if (state?.key !== key) return <div className={styles.loading} role="status">Loading impact graph…</div>;
  if (state.error) return <div className={styles.error} role="alert"><h2>Impact graph unavailable</h2><p>{state.error}</p><button className="button button--secondary" type="button" onClick={() => { setState(undefined); setAttempt((value) => value + 1); }}>Try again</button></div>;
  return state.graph && <GraphView key={`${key}/${state.graph.revision}/${attempt}`} graph={state.graph} demo={demo} />;
}
