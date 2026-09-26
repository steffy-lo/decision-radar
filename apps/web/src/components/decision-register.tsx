"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { EmptyState, Eyebrow, PageHeading, Panel, StatusPill } from "@/components/ui";
import { parseDemoFixture, type DemoFixture, type Decision } from "@/lib/domain/models";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; data: DemoFixture }
  | { kind: "error"; message: string };

const demoId = "proj_demo_2026";

function displayDate(value: string) {
  const date = new Date(`${value}T00:00:00Z`);
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(date);
}

export function DecisionRegister({ projectId }: { projectId: string }) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "active" | "draft">("all");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const path = projectId === demoId
      ? `/api/v1/projects/${encodeURIComponent(projectId)}/fixture`
      : `/api/v1/projects/${encodeURIComponent(projectId)}/decisions`;
    fetch(path, { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Could not load decisions (${response.status}).`);
        return response.json();
      })
      .then((value) => {
        if (projectId !== demoId) throw new Error("The live decision API is not available yet.");
        setState({ kind: "ready", data: parseDemoFixture(value) });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({ kind: "error", message: error instanceof Error ? error.message : "Could not load decisions." });
      });
    return () => controller.abort();
  }, [projectId, refreshKey]);

  const data = state.kind === "ready" ? state.data : null;
  const visible = useMemo(() => {
    if (!data) return [];
    const search = query.trim().toLowerCase();
    return data.decisions.filter((decision) =>
      (filter === "all" || decision.status === filter) &&
      (!search || [decision.statement, decision.owner, decision.rationale].some((text) => text.toLowerCase().includes(search))),
    );
  }, [data, filter, query]);

  const activeCount = data?.decisions.filter((decision) => decision.status === "active").length ?? 0;
  const challengedCount = data?.alerts.filter((alert) => alert.reviewState === "open").length ?? 0;

  return (
    <>
      <PageHeading
        eyebrow="DECISION INTELLIGENCE"
        title="Decision register"
        description="The reasoning behind every decision, connected to the evidence that can change it."
        action={<Link className="button button--primary" href={`/projects/${encodeURIComponent(projectId)}/reviews`}>View review queue <span aria-hidden="true">↗</span></Link>}
      />

      <div className="overview-grid">
        <Panel className="metric-card">
          <span className="metric-card__icon metric-card__icon--teal" aria-hidden="true">◈</span>
          <span className="metric-card__label">Active decisions</span>
          <strong>{state.kind === "loading" ? "—" : activeCount.toString().padStart(2, "0")}</strong>
          <small>In this workspace</small>
        </Panel>
        <Panel className="metric-card">
          <span className="metric-card__icon metric-card__icon--amber" aria-hidden="true">!</span>
          <span className="metric-card__label">Needs review</span>
          <strong>{state.kind === "loading" ? "—" : challengedCount.toString().padStart(2, "0")}</strong>
          <small>Assumptions challenged</small>
        </Panel>
        <Panel className="metric-card">
          <span className="metric-card__icon metric-card__icon--violet" aria-hidden="true">⌁</span>
          <span className="metric-card__label">Connected evidence</span>
          <strong>{state.kind === "loading" ? "—" : (data?.sources.length ?? 0).toString().padStart(2, "0")}</strong>
          <small>Project sources in view</small>
        </Panel>
      </div>

      {challengedCount > 0 && (
        <div className="signal-banner" role="status">
          <span className="signal-banner__icon" aria-hidden="true">✳</span>
          <div>
            <strong>A decision needs your attention</strong>
            <p>Vendor delivery has moved beyond a confirmed deadline. Review the evidence and downstream impact.</p>
          </div>
          <Link href={`/projects/${encodeURIComponent(projectId)}/reviews`}>Review signal <span aria-hidden="true">→</span></Link>
        </div>
      )}

      <div className="section-heading">
        <div><Eyebrow>YOUR WORKSPACE</Eyebrow><h2>Decisions</h2></div>
        <span className="section-heading__count">{data?.decisions.length ?? 0} total</span>
      </div>

      <div className="toolbar">
        <label className="search-field">
          <span aria-hidden="true">⌕</span>
          <span className="sr-only">Search decisions</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search decisions..." />
        </label>
        <div className="segmented-control" role="group" aria-label="Filter decisions">
          {(["all", "active", "draft"] as const).map((value) => (
            <button
              key={value}
              type="button"
              className={filter === value ? "is-selected" : ""}
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
            >
              {value === "all" ? "All" : value === "active" ? "Active" : "Draft"}
            </button>
          ))}
        </div>
      </div>

      {state.kind === "loading" ? (
        <div className="decision-list" aria-busy="true" aria-label="Loading decisions">
          {[0, 1, 2].map((item) => <Panel className="decision-skeleton" key={item}><div /><div /><div /></Panel>)}
        </div>
      ) : state.kind === "error" ? (
        <EmptyState
          title="Decisions could not be loaded"
          description={state.message}
          action={<button className="button button--secondary" type="button" onClick={() => { setState({ kind: "loading" }); setRefreshKey((value) => value + 1); }}>Try again</button>}
        />
      ) : visible.length === 0 ? (
        <EmptyState title="No decisions found" description={query ? "Try a different search or filter." : "Confirmed decisions will appear here once they are added to this project."} />
      ) : (
        <div className="decision-list">
          {visible.map((decision) => <DecisionCard key={decision.id} decision={decision} data={state.data} projectId={projectId} />)}
        </div>
      )}
      <p className="page-footnote">This workspace is showing synthetic evidence for the prototype demonstration.</p>
    </>
  );
}

function DecisionCard({ decision, data, projectId }: { decision: Decision; data: DemoFixture; projectId: string }) {
  const assumptions = data.assumptions.filter((item) => item.decisionId === decision.id);
  const alert = data.alerts.find((item) => item.decisionId === decision.id && item.reviewState === "open");
  const finding = alert ? data.findings.find((item) => item.id === alert.findingId) : undefined;
  const dateAssumption = assumptions.find((item) => item.expectedValue.type === "date");
  return (
    <Panel className={`decision-card ${alert ? "decision-card--challenged" : ""}`}>
      <div className="decision-card__top">
        <div className="decision-card__identity">
          <span className="decision-card__symbol" aria-hidden="true">{alert ? "!" : "◈"}</span>
          <div>
            <div className="decision-card__meta">DECISION <span>·</span> REVISION {decision.activeRevision}</div>
            <h3>{decision.statement}</h3>
          </div>
        </div>
        <StatusPill tone={alert ? "warning" : "success"}>{alert ? "Needs review" : decision.status === "active" ? "Active" : "Draft"}</StatusPill>
      </div>
      <p className="decision-card__rationale">{decision.rationale}</p>
      <div className="decision-card__details">
        <div><small>OWNER</small><strong>{decision.owner}</strong></div>
        <div><small>ASSUMPTIONS</small><strong>{assumptions.length} monitored</strong></div>
        {dateAssumption?.expectedValue.type === "date" && <div><small>KEY DATE</small><strong>{displayDate(dateAssumption.expectedValue.value)}</strong></div>}
      </div>
      {finding && (
        <div className="decision-card__signal">
          <span className="decision-card__signal-icon" aria-hidden="true">↗</span>
          <span>Vendor delivery moved <strong>+{finding.deltaDays} days</strong> beyond the required date.</span>
          <Link href={`/projects/${encodeURIComponent(projectId)}/reviews`}>View evidence <span aria-hidden="true">→</span></Link>
        </div>
      )}
    </Panel>
  );
}
