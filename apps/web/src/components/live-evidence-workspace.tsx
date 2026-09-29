"use client";

import { useCallback, useEffect, useState } from "react";
import { DriveConnectionPanel } from "@/components/connections/drive-connection-panel";
import {
  extractSource, getAssessmentResults, getCurrentProjectMembership, getExtraction,
  listMonitoredAssumptions, listSources, runAssessment,
} from "@/lib/api/client";
import type {
  AssessmentResults, ExtractionResult, MonitoredAssumption, ProjectMembership, SourceSummary,
} from "@/lib/api/client";
import { EmptyState, PageHeading, Panel, StatusPill } from "@/components/ui";

function errorText(value: unknown): string {
  return value instanceof Error ? value.message : "The request failed. Please try again.";
}

export function LiveSourcesWorkspace({ projectId }: { projectId: string }) {
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [assumptions, setAssumptions] = useState<MonitoredAssumption[]>([]);
  const [selectedAssumption, setSelectedAssumption] = useState("");
  const [entityAlias, setEntityAlias] = useState("");
  const [predicateAlias, setPredicateAlias] = useState("");
  const [extractions, setExtractions] = useState<Record<string, ExtractionResult>>({});
  const [busySource, setBusySource] = useState<string | null>(null);
  const [membership, setMembership] = useState<ProjectMembership | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextSources, nextAssumptions, nextMembership] = await Promise.all([
        listSources(projectId), listMonitoredAssumptions(projectId), getCurrentProjectMembership(projectId),
      ]);
      setSources(nextSources);
      setAssumptions(nextAssumptions);
      setMembership(nextMembership);
      setSelectedAssumption((current) => nextAssumptions.some((row) => row.id === current) ? current : nextAssumptions[0]?.id ?? "");
      const prior = await Promise.all(nextSources.map(async (source) => [source.id, await getExtraction(projectId, source.id)] as const));
      setExtractions(Object.fromEntries(prior.filter((entry) => entry[1] !== null)) as Record<string, ExtractionResult>);
      setError(null);
    } catch (value) {
      setError(errorText(value));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  const selected = assumptions.find((row) => row.id === selectedAssumption);
  async function runExtraction(sourceId: string) {
    if (!selected || !entityAlias.trim() || !predicateAlias.trim()) {
      setError("Choose an active assumption and enter the entity and predicate wording from the source.");
      return;
    }
    setBusySource(sourceId);
    setError(null);
    try {
      const result = await extractSource(projectId, sourceId, selected.id, entityAlias.trim(), predicateAlias.trim());
      setExtractions((current) => ({ ...current, [sourceId]: result }));
    } catch (value) {
      setError(errorText(value));
    } finally {
      setBusySource(null);
    }
  }

  return <>
    <PageHeading eyebrow="PROJECT EVIDENCE" title="Sources" description="Bring project updates into one place and turn source text into facts you can review." />
    <DriveConnectionPanel projectId={projectId} onSourcesChanged={() => void load()} />
    {error && <p role="alert" className="notice notice--error">{error}</p>}
    <Panel className="workspace-card workspace-card--spaced">
      <div className="flow-card-heading"><span className="flow-step">2</span><div className="flow-card-heading__copy"><span className="overline">FACT EXTRACTION</span><h2>Match source wording</h2><p>Choose an assumption, then enter the words used in the source. Verified facts can then be assessed.</p></div></div>
      <label className="form-field">Monitored assumption
        <select className="form-control" value={selectedAssumption} onChange={(event) => setSelectedAssumption(event.target.value)}>
          {assumptions.length === 0 && <option value="">No active assumptions</option>}
          {assumptions.map((row) => <option key={row.id} value={row.id}>{row.decisionStatement}: {row.statement}</option>)}
        </select>
      </label>
      {selected && <p className="field-help">Trusted entity: {selected.entityId} · predicate: {selected.predicate}</p>}
      <div className="form-grid form-grid--two">
        <label className="form-field">Entity wording in source<input className="form-control" value={entityAlias} onChange={(event) => setEntityAlias(event.target.value)} placeholder="e.g. Acme Logistics" /></label>
        <label className="form-field">Predicate wording in source<input className="form-control" value={predicateAlias} onChange={(event) => setPredicateAlias(event.target.value)} placeholder="e.g. delivery date" /></label>
      </div>
      {assumptions.length === 0 && <p className="notice notice--warning">Confirm a decision with a monitored assumption before extracting facts.</p>}
    </Panel>
    <div className="workspace-section">
      <div className="workspace-section__heading"><div><span className="overline">SOURCE LIBRARY</span><h2>Connected sources</h2></div><span className="section-count">{sources.length} files</span></div>
      {loading ? <p className="supporting-copy">Loading sources…</p> : sources.length === 0 ? <EmptyState title="No sources yet" description="Connect Drive and refresh a folder to bring its files into this project." /> : <div className="workspace-stack">{sources.map((source) => {
        const result = extractions[source.id];
        return <Panel className="workspace-card source-item" key={source.id}>
          <div className="source-item__head"><div><h3>{source.name}</h3><a href={source.native_url} target="_blank" rel="noopener noreferrer" className="text-link">Open source ↗</a></div><StatusPill tone="success">{source.status}</StatusPill></div>
          {membership?.role !== "viewer" && <button className="button button--primary" disabled={busySource !== null || !selected} onClick={() => void runExtraction(source.id)}>{busySource === source.id ? "Extracting…" : "Extract with Gemini"}</button>}
          {result && <div className="source-item__results"><p role="status" className="notice notice--success">{result.publishedFactCount} verified facts ready for assessment</p>
            {result.facts.map((fact, index) => <div key={`${source.id}-${index}`} className="fact-card"><div><strong>{fact.entity} · {fact.predicate}</strong><StatusPill>{fact.state}</StatusPill></div><blockquote>“{fact.quote}”</blockquote>{fact.uncertainReason && <p className="notice notice--warning">{fact.uncertainReason}</p>}</div>)}
            {result.decisions.map((decision, index) => <div key={`decision-${index}`} className="fact-card"><strong>Suggested decision</strong><p>{decision.statement}</p>{decision.uncertainReason && <p className="notice notice--warning">{decision.uncertainReason}</p>}</div>)}
          </div>}
        </Panel>;
      })}</div>}
    </div>
  </>;
}

export function LiveReviewsWorkspace({ projectId }: { projectId: string }) {
  const [data, setData] = useState<AssessmentResults | null>(null);
  const [membership, setMembership] = useState<ProjectMembership | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try {
      const [next, member] = await Promise.all([getAssessmentResults(projectId), getCurrentProjectMembership(projectId)]);
      setData(next); setMembership(member); setError(null);
    } catch (value) { setError(errorText(value)); }
  }, [projectId]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  async function assess() {
    setBusy(true); setError(null);
    try { await runAssessment(projectId); await load(); }
    catch (value) { setError(errorText(value)); }
    finally { setBusy(false); }
  }
  return <>
    <PageHeading eyebrow="REVIEW QUEUE" title="Reviews" description="Check confirmed decisions against verified source facts." action={membership?.role !== "viewer" && <button className="button button--primary" disabled={busy} onClick={() => void assess()}>{busy ? "Running assessment…" : "Run assessment"}</button>} />
    {error && <p role="alert" className="notice notice--error">{error}</p>}
    <div className="review-summary workspace-card"><div><span className="overline">LATEST ASSESSMENT</span><h2>{data?.latestRun ? `${data.latestRun.alertCount} ${data.latestRun.alertCount === 1 ? "alert" : "alerts"} to review` : "Ready to assess"}</h2><p>{data?.latestRun ? `${data.latestRun.findingCount} ${data.latestRun.findingCount === 1 ? "finding" : "findings"} checked in the latest run.` : "Run an assessment after you confirm decisions and extract source facts."}</p></div><span className="review-summary__symbol" aria-hidden="true">◇</span></div>
    <div className="workspace-section workspace-stack">{data?.alerts.length ? data.alerts.map((alert) => {
      const finding = data.findings.find((row) => row.id === alert.findingId);
      return <Panel key={alert.id} className="workspace-card review-item"><div className="source-item__head"><div><span className="overline">DECISION ALERT</span><h2>Decision needs review</h2></div><StatusPill tone="warning">{alert.severity}</StatusPill></div>
        <div className="review-delta"><strong>{finding?.reasonCode === "DATE_AFTER_REQUIRED_BY" ? "Date moved past the target" : finding?.reasonCode?.replaceAll("_", " ") ?? "Source update"}</strong>{finding?.deltaDays != null && <span>{finding.deltaDays} days later</span>}</div>
        {finding && <div className="review-evidence"><div><span className="overline">ORIGINAL EVIDENCE</span><blockquote>“{finding.baselineEvidence.quote}”</blockquote></div><div><span className="overline">NEW EVIDENCE</span><blockquote>“{finding.updateEvidence.quote}”</blockquote></div></div>}
      </Panel>;
    }) : <EmptyState title="No alerts to review" description="Run an assessment after extracting facts from your connected sources." />}</div>
  </>;
}
