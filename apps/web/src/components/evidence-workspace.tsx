"use client";

import { useMemo } from "react";
import { EvidenceReference } from "@/components/evidence-reference";
import { ImpactGraph } from "@/components/graph/impact-graph";
import { EmptyState, PageHeading, Panel, StatusPill } from "@/components/ui";
import { isDemoProject, useProjectData } from "@/lib/demo/use-project-data";
import { createWorkspaceView } from "@/lib/demo/workspace-view";
import { LiveReviewsWorkspace, LiveSourcesWorkspace } from "@/components/live-evidence-workspace";
import type { EvidenceRef, Source } from "@/lib/domain/models";

function snapshotLocator(source: Source | undefined, evidence: EvidenceRef): string | undefined {
  if (!source || source.status !== "ready") return undefined;
  const start = source.contentSnapshot.indexOf(evidence.quote);
  return start < 0 ? undefined : `Snapshot characters ${start + 1}–${start + evidence.quote.length}`;
}

function EvidenceLoading() {
  return <div className="route-loading" aria-busy="true" aria-label="Loading evidence"><div className="route-loading__panel" /></div>;
}

export function SourcesWorkspace({ projectId }: { projectId: string }) {
  return isDemoProject(projectId) ? <FixtureSourcesWorkspace projectId={projectId} /> : <LiveSourcesWorkspace projectId={projectId} />;
}

function FixtureSourcesWorkspace({ projectId }: { projectId: string }) {
  const { status, data, error, retry } = useProjectData(projectId);
  const workspace = useMemo(() => data ? createWorkspaceView(data) : null, [data]);
  return <>
    <PageHeading eyebrow="PROJECT EVIDENCE" title="Sources" description="The documents and meeting notes that ground your decisions." />
    {status === "loading" ? <EvidenceLoading /> : status === "error" ?
      <EmptyState title="Sources could not be loaded" description={error ?? "Could not load project data."} action={<button className="button button--secondary" type="button" onClick={retry}>Try again</button>} /> :
      workspace?.sources.length === 0 ? <EmptyState title="No sources yet" description="Connected documents will appear here." /> :
      <div className="evidence-list">{workspace?.sources.map((source) => <Panel className="source-card" key={source.id}>
        <div className="source-card__head"><span className="source-card__icon" aria-hidden="true">▤</span><div><span className="eyebrow">{source.status === "ready" ? "GOOGLE DOC" : "SOURCE"}</span><h2>{source.name}</h2></div><StatusPill tone={source.status === "ready" ? "success" : "warning"}>{source.status === "ready" ? "Ready" : "Access unavailable"}</StatusPill></div>
        <p>{source.status === "ready" ? source.contentSnapshot : "Source details are hidden until access is restored."}</p>
        <small>Synthetic source for the prototype demonstration</small>
      </Panel>)}</div>}
  </>;
}

export function ReviewsWorkspace({ projectId, alertId }: { projectId: string; alertId?: string }) {
  return isDemoProject(projectId)
    ? <FixtureReviewsWorkspace projectId={projectId} alertId={alertId} />
    : <LiveReviewsWorkspace projectId={projectId} alertId={alertId} />;
}

function FixtureReviewsWorkspace({ projectId, alertId }: { projectId: string; alertId?: string }) {
  const { status, data, error, retry } = useProjectData(projectId);
  const workspace = useMemo(() => data ? createWorkspaceView(data) : null, [data]);
  const open = workspace?.openReviews ?? [];
  return <>
    <PageHeading eyebrow="REVIEW QUEUE" title="Reviews" description="Compare confirmed assumptions with new evidence before changing a decision." />
    {alertId && <ImpactGraph key={`${projectId}/${alertId}`} projectId={projectId} alertId={alertId} severity={data?.alerts.find((alert) => alert.id === alertId)?.severity} />}
    {status === "loading" ? <EvidenceLoading /> : status === "error" ?
      <EmptyState title="Reviews could not be loaded" description={error ?? "Could not load project data."} action={<button className="button button--secondary" type="button" onClick={retry}>Try again</button>} /> : open.length === 0 ?
      data?.sources.some((source) => source.status !== "ready")
        ? <EmptyState title="Evidence unclear" description="A source needed for this review is unavailable. Restore access and assess it before drawing a conclusion." />
        : <EmptyState title="No detected issue in assessed sources" description="The available source facts in this synthetic assessment do not contradict a monitored assumption." /> :
      <div className="evidence-list">{open.map(({ alert, decision, finding, dependencies }) =>
        <Panel className="review-card" key={alert.id}>
          <div className="review-card__head"><div><span className="eyebrow">CHALLENGED DECISION</span><h2>{decision.statement}</h2></div><StatusPill tone="warning">Needs review</StatusPill></div>
          <p className="review-card__summary">A confirmed update conflicts with the delivery date behind this launch decision.</p>
          <p className="review-card__meta">Classification: {finding.classification} · {data?.sources.some((source) => source.id === finding.updateEvidence.sourceId && source.status !== "ready") ? "Evidence unclear: source access unavailable" : "Coverage: assessed from exact source quotes"}</p>
          <div className="review-delta"><span>Expected by <strong>{finding.baselineValue.value}</strong></span><span aria-hidden="true">→</span><span>Now confirmed <strong>{finding.extractedValue.value}</strong></span><strong>+{finding.deltaDays} days</strong></div>
          <div className="review-evidence">
            {[finding.baselineEvidence, finding.updateEvidence].map((evidence, index) => { const source = data?.sources.find((row) => row.id === evidence.sourceId); return <EvidenceReference key={`${alert.id}-${index}`} evidence={evidence} label={index === 0 ? "ORIGINAL ASSUMPTION" : "NEW EVIDENCE"} available={source?.status === "ready"} sourceType={source?.mimeType} locator={snapshotLocator(source, evidence)} demoSourceText={source?.contentSnapshot} />; })}
          </div>
          <div className="review-impact"><strong>Potential downstream impact</strong>{dependencies.map((item) => <p key={item.id}>{item.impactDescription}</p>)}</div>
          <a className="text-link" href={`/projects/${encodeURIComponent(projectId)}/reviews?alertId=${encodeURIComponent(alert.id)}`}>View impact graph →</a>
          <p className="review-card__note">Review actions and revision history will be enabled when the review workflow is connected.</p>
        </Panel>)}</div>}
    <p className="page-footnote">Synthetic demo states: <a className="text-link" href={`/projects/${encodeURIComponent(projectId)}/reviews`}>Needs review</a> · <a className="text-link" href={`/projects/${encodeURIComponent(projectId)}/reviews?scenario=access-unavailable`}>Access unavailable</a> · <a className="text-link" href={`/projects/${encodeURIComponent(projectId)}/reviews?scenario=evidence-unclear`}>Evidence unclear</a> · <a className="text-link" href={`/projects/${encodeURIComponent(projectId)}/reviews?scenario=no-detected-issue`}>No detected issue</a></p>
  </>;
}
