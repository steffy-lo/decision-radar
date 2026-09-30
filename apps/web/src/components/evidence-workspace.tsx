"use client";

import type { ReactNode } from "react";
import { useMemo } from "react";
import { EmptyState, PageHeading, Panel, StatusPill } from "@/components/ui";
import { isDemoProject, useProjectData } from "@/lib/demo/use-project-data";
import { createWorkspaceView } from "@/lib/demo/workspace-view";

function EvidenceLoading() {
  return <div className="route-loading" aria-busy="true" aria-label="Loading evidence"><div className="route-loading__panel" /></div>;
}

export function SourcesWorkspace({ projectId, connectionControl }: { projectId: string; connectionControl?: ReactNode }) {
  const { status, data, error, retry } = useProjectData(projectId);
  const workspace = useMemo(() => data ? createWorkspaceView(data) : null, [data]);
  return <>
    <PageHeading eyebrow="PROJECT EVIDENCE" title="Sources" description="The documents and meeting notes that ground your decisions." />
    {connectionControl}
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

export function ReviewsWorkspace({ projectId }: { projectId: string }) {
  const { status, data, error, retry } = useProjectData(projectId);
  const workspace = useMemo(() => data ? createWorkspaceView(data) : null, [data]);
  const open = workspace?.openReviews ?? [];
  return <>
    <PageHeading eyebrow="REVIEW QUEUE" title="Reviews" description="Compare confirmed assumptions with new evidence before changing a decision." />
    {status === "loading" ? <EvidenceLoading /> : status === "error" ?
      <EmptyState title="Reviews could not be loaded" description={error ?? "Could not load project data."} action={<button className="button button--secondary" type="button" onClick={retry}>Try again</button>} /> : open.length === 0 ?
      <EmptyState title="Nothing needs review" description="New conflicts with confirmed assumptions will appear here." /> :
      <div className="evidence-list">{open.map(({ alert, decision, finding, dependencies }) =>
        <Panel className="review-card" key={alert.id}>
          <div className="review-card__head"><div><span className="eyebrow">CHALLENGED DECISION</span><h2>{decision.statement}</h2></div><StatusPill tone="warning">Needs review</StatusPill></div>
          <p className="review-card__summary">A confirmed vendor update conflicts with the delivery date behind this launch decision.</p>
          <div className="review-delta"><span>Expected by <strong>{finding.baselineValue.value}</strong></span><span aria-hidden="true">→</span><span>Now confirmed <strong>{finding.extractedValue.value}</strong></span><strong>+{finding.deltaDays} days</strong></div>
          <div className="review-evidence">
            <div><span className="eyebrow">ORIGINAL ASSUMPTION</span><blockquote>“{finding.baselineEvidence.quote}”</blockquote><small>{finding.baselineEvidence.sourceTitle}</small></div>
            <div><span className="eyebrow">NEW EVIDENCE</span><blockquote>“{finding.updateEvidence.quote}”</blockquote><small>{finding.updateEvidence.sourceTitle}</small></div>
          </div>
          <div className="review-impact"><strong>Potential downstream impact</strong>{dependencies.map((item) => <p key={item.id}>{item.impactDescription}</p>)}</div>
          <p className="review-card__note">Review actions and revision history will be enabled when the review workflow is connected.</p>
        </Panel>)}</div>}
    {isDemoProject(projectId) && <p className="page-footnote">This workspace is showing synthetic evidence for the prototype demonstration.</p>}
  </>;
}
