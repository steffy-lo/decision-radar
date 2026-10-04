"use client";

import type { ReactNode } from "react";
import { useMemo } from "react";
import { EmptyState, PageHeading, Panel, StatusPill } from "@/components/ui";
import { isDemoProject, useProjectData } from "@/lib/demo/use-project-data";
import { createWorkspaceView } from "@/lib/demo/workspace-view";
import { ImpactGraph } from "@/components/graph/impact-graph";

function EvidenceLoading() {
  return <div className="route-loading" aria-busy="true" aria-label="Loading evidence"><div className="route-loading__panel" /></div>;
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
        <div className="source-card__head"><span className="source-card__icon" aria-hidden="true">▤</span><div><span className="eyebrow">GOOGLE DOC</span><h2>{source.name}</h2></div><StatusPill tone="success">Ready</StatusPill></div>
        <p>{source.contentSnapshot}</p>
        <small>Synthetic source for the prototype demonstration</small>
      </Panel>)}</div>}
  </>;
}

export function SourcesWorkspace({ projectId, connectionControl }: { projectId: string; connectionControl?: ReactNode }) {
  if (isDemoProject(projectId)) return <FixtureSourcesWorkspace projectId={projectId} />;
  return <>
    <PageHeading eyebrow="PROJECT EVIDENCE" title="Sources" description="The documents and meeting notes that ground your decisions." />
    {connectionControl}
  </>;
}

export function ReviewsWorkspace({ projectId, alertId }: { projectId: string; alertId?: string }) {
  if (alertId) return <>
    <PageHeading eyebrow="REVIEW QUEUE" title="Reviews" description="Follow the evidence and recorded dependencies before changing a decision." />
    <ImpactGraph key={`${projectId}/${alertId}`} projectId={projectId} alertId={alertId} />
    {isDemoProject(projectId) && <p className="page-footnote">This workspace is showing synthetic evidence for the prototype demonstration.</p>}
  </>;
  return <ReviewQueue projectId={projectId} />;
}

function ReviewQueue({ projectId }: { projectId: string }) {
  const { status, data, error, retry } = useProjectData(projectId);
  const workspace = useMemo(() => data ? createWorkspaceView(data) : null, [data]);
  const open = workspace?.openReviews ?? [];
  return <>
    <PageHeading eyebrow="REVIEW QUEUE" title="Reviews" description="Compare confirmed assumptions with new evidence before changing a decision." />
    {status === "loading" ? <EvidenceLoading /> : status === "error" ?
      <EmptyState title="Reviews could not be loaded" description={error ?? "Could not load project data."} action={<button className="button button--secondary" type="button" onClick={retry}>Try again</button>} /> : open.length === 0 ?
      <EmptyState title="Nothing needs review" description="New conflicts with confirmed assumptions will appear here." /> :
      <div className="evidence-list">{open.map(({ alert, decision, finding }) =>
        <div key={alert.id}>
        <Panel className="review-card">
          <div className="review-card__head"><div><span className="eyebrow">CHALLENGED DECISION</span><h2>{decision.statement}</h2></div><StatusPill tone="warning">Needs review</StatusPill></div>
          <p className="review-card__summary">New evidence challenges a confirmed assumption. Inspect the impact map below to follow the recorded effects.</p>
          <div className="review-delta"><span>Expected <strong>{finding.baselineValue.value}</strong></span><span aria-hidden="true">→</span><span>Updated <strong>{finding.extractedValue.value}</strong></span>{finding.deltaDays !== null && <strong>{finding.deltaDays > 0 ? "+" : ""}{finding.deltaDays} days</strong>}</div>
          <p className="review-card__note">Review actions and revision history will be enabled when the review workflow is connected.</p>
        </Panel>
        <ImpactGraph projectId={projectId} alertId={alert.id} />
        </div>)}</div>}
    {isDemoProject(projectId) && <p className="page-footnote">This workspace is showing synthetic evidence for the prototype demonstration.</p>}
  </>;
}
