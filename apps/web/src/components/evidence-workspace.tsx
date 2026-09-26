"use client";

import { useEffect, useState } from "react";
import { EmptyState, PageHeading, Panel, StatusPill } from "@/components/ui";
import { parseDemoFixture, type DemoFixture } from "@/lib/domain/models";

type State = { kind: "loading" } | { kind: "ready"; data: DemoFixture } | { kind: "error"; message: string };

function useDemoEvidence(projectId: string): State {
  const [state, setState] = useState<State>({ kind: "loading" });
  useEffect(() => {
    if (projectId !== "proj_demo_2026") return;
    const controller = new AbortController();
    fetch(`/api/v1/projects/${encodeURIComponent(projectId)}/fixture`, { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Could not load evidence (${response.status}).`);
        return response.json();
      })
      .then((value) => setState({ kind: "ready", data: parseDemoFixture(value) }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ kind: "error", message: error instanceof Error ? error.message : "Could not load evidence." });
      });
    return () => controller.abort();
  }, [projectId]);
  return projectId === "proj_demo_2026" ? state : { kind: "error", message: "Live project evidence is not connected yet." };
}

function EvidenceLoading() {
  return <div className="route-loading" aria-busy="true" aria-label="Loading evidence"><div className="route-loading__panel" /></div>;
}

export function SourcesWorkspace({ projectId }: { projectId: string }) {
  const state = useDemoEvidence(projectId);
  return <>
    <PageHeading eyebrow="PROJECT EVIDENCE" title="Sources" description="The documents and meeting notes that ground your decisions." />
    {state.kind === "loading" ? <EvidenceLoading /> : state.kind === "error" ?
      <EmptyState title="Sources could not be loaded" description={state.message} /> :
      state.data.sources.length === 0 ? <EmptyState title="No sources yet" description="Connected documents will appear here." /> :
      <div className="evidence-list">{state.data.sources.map((source) => <Panel className="source-card" key={source.id}>
        <div className="source-card__head"><span className="source-card__icon" aria-hidden="true">▤</span><div><span className="eyebrow">GOOGLE DOC</span><h2>{source.name}</h2></div><StatusPill tone="success">Ready</StatusPill></div>
        <p>{source.contentSnapshot}</p>
        <small>Synthetic source for the prototype demonstration</small>
      </Panel>)}</div>}
  </>;
}

export function ReviewsWorkspace({ projectId }: { projectId: string }) {
  const state = useDemoEvidence(projectId);
  const data = state.kind === "ready" ? state.data : null;
  const open = data?.alerts.filter((alert) => alert.reviewState === "open") ?? [];
  return <>
    <PageHeading eyebrow="REVIEW QUEUE" title="Reviews" description="Compare confirmed assumptions with new evidence before changing a decision." />
    {state.kind === "loading" ? <EvidenceLoading /> : state.kind === "error" ?
      <EmptyState title="Reviews could not be loaded" description={state.message} /> : open.length === 0 ?
      <EmptyState title="Nothing needs review" description="New conflicts with confirmed assumptions will appear here." /> :
      <div className="evidence-list">{open.map((alert) => {
        const decision = data?.decisions.find((item) => item.id === alert.decisionId);
        const finding = data?.findings.find((item) => item.id === alert.findingId);
        if (!decision || !finding) return null;
        return <Panel className="review-card" key={alert.id}>
          <div className="review-card__head"><div><span className="eyebrow">CHALLENGED DECISION</span><h2>{decision.statement}</h2></div><StatusPill tone="warning">Needs review</StatusPill></div>
          <p className="review-card__summary">A confirmed vendor update conflicts with the delivery date behind this launch decision.</p>
          <div className="review-delta"><span>Expected by <strong>{finding.baselineValue.value}</strong></span><span aria-hidden="true">→</span><span>Now confirmed <strong>{finding.extractedValue.value}</strong></span><strong>+{finding.deltaDays} days</strong></div>
          <div className="review-evidence">
            <div><span className="eyebrow">ORIGINAL ASSUMPTION</span><blockquote>“{finding.baselineEvidence.quote}”</blockquote><small>{finding.baselineEvidence.sourceTitle}</small></div>
            <div><span className="eyebrow">NEW EVIDENCE</span><blockquote>“{finding.updateEvidence.quote}”</blockquote><small>{finding.updateEvidence.sourceTitle}</small></div>
          </div>
          <div className="review-impact"><strong>Potential downstream impact</strong>{data?.dependencies.filter((item) => item.fromDecisionId === decision.id).map((item) => <p key={item.id}>{item.impactDescription}</p>)}</div>
          <p className="review-card__note">Review actions and revision history will be enabled when the review workflow is connected.</p>
        </Panel>;
      })}</div>}
    <p className="page-footnote">This workspace is showing synthetic evidence for the prototype demonstration.</p>
  </>;
}
