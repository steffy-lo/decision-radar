"use client";

import { useCallback, useEffect, useState } from "react";
import { DriveConnectionPanel } from "@/components/connections/drive-connection-panel";
import { EvidenceReference } from "@/components/evidence-reference";
import { ImpactGraph } from "@/components/graph/impact-graph";
import { ReviewActionPanel } from "@/components/review-action-panel";
import { TableMappingForm } from "@/components/table-mapping-form";
import {
  extractSource, getAssessmentResults, getCurrentProjectMembership, getExtraction,
  getJob, listMonitoredAssumptions, listSources, retryJob, submitAnalysisJob,
} from "@/lib/api/client";
import type {
  AssessmentResults, BackgroundJob, ExtractionResult, MonitoredAssumption, ProjectMembership, SourceSummary,
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
      <div className="flow-card-heading"><span className="flow-step">2</span><div className="flow-card-heading__copy"><span className="section-kicker">FACT EXTRACTION</span><h2>Match source wording</h2><p>Choose an assumption and enter how Gemini should identify its entity and predicate. If a candidate stays unresolved, check that it refers to this assumption before using Gemini’s wording.</p></div></div>
      <label className="form-field">Monitored assumption
        <select className="form-control" value={selectedAssumption} onChange={(event) => setSelectedAssumption(event.target.value)}>
          {assumptions.length === 0 && <option value="">No active assumptions</option>}
          {assumptions.map((row) => <option key={row.id} value={row.id}>{row.decisionStatement}: {row.statement}</option>)}
        </select>
      </label>
      {selected && <p className="field-help">Trusted entity: {selected.entityId} · predicate: {selected.predicate}</p>}
      <div className="form-grid form-grid--two">
        <label className="form-field">Entity wording Gemini uses<input className="form-control" value={entityAlias} onChange={(event) => setEntityAlias(event.target.value)} placeholder="e.g. Acme Logistics" /></label>
        <label className="form-field">Predicate wording Gemini uses<input className="form-control" value={predicateAlias} onChange={(event) => setPredicateAlias(event.target.value)} placeholder="e.g. delivery date" /></label>
      </div>
      {assumptions.length === 0 && <p className="notice notice--warning">Confirm a decision with a monitored assumption before extracting facts.</p>}
    </Panel>
    <div className="workspace-section">
      <div className="workspace-section__heading"><div><span className="section-kicker">SOURCE LIBRARY</span><h2>Connected sources</h2></div><span className="section-count">{sources.length} files</span></div>
      {loading ? <p className="supporting-copy">Loading sources…</p> : sources.length === 0 ? <EmptyState title="No sources yet" description="Connect Drive and refresh a folder to bring its files into this project." /> : <div className="workspace-stack">{sources.map((source) => {
        const result = extractions[source.id];
        return <Panel className="workspace-card source-item" key={source.id}>
          <div className="source-item__head"><div><h3>{source.name}</h3><a href={source.native_url} target="_blank" rel="noopener noreferrer" className="text-link">Open source ↗</a></div><StatusPill tone={source.status === "ready" ? "success" : "warning"}>{source.failure_reason === "removed_from_folder" ? "Removed from folder" : source.status}</StatusPill></div>
          {source.failure_reason && <p role="status" className="notice notice--warning">{source.failure_reason}</p>}
          {membership?.role !== "viewer" && ["application/vnd.google-apps.spreadsheet", "text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"].includes(source.mime_type) && <TableMappingForm projectId={projectId} source={source} onSaved={load} />}
          {membership?.role !== "viewer" && !["application/vnd.google-apps.spreadsheet", "text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"].includes(source.mime_type) && <button className="button button--primary" disabled={busySource !== null || !selected || source.status !== "ready"} onClick={() => void runExtraction(source.id)}>{busySource === source.id ? "Extracting…" : "Extract with Gemini"}</button>}
          {result && <div className="source-item__results"><p role="status" className={`notice ${result.publishedFactCount ? "notice--success" : "notice--warning"}`}>{result.publishedFactCount} verified facts ready for assessment</p>
            {result.facts.map((fact, index) => <div key={`${source.id}-${index}`} className="fact-card"><div><strong>{fact.entity} · {fact.predicate}</strong><StatusPill>{fact.state}</StatusPill></div><blockquote>“{fact.quote}”</blockquote>{fact.uncertainReason && <p className="notice notice--warning">{fact.uncertainReason}</p>}{fact.uncertainReason?.includes("unresolved") && membership?.role !== "viewer" && <div className="fact-card__actions"><button className="button button--secondary" type="button" onClick={() => setEntityAlias(fact.entity)}>Use entity wording</button><button className="button button--secondary" type="button" onClick={() => setPredicateAlias(fact.predicate)}>Use predicate wording</button></div>}</div>)}
            {result.decisions.map((decision, index) => <div key={`decision-${index}`} className="fact-card"><strong>Suggested decision</strong><p>{decision.statement}</p>{decision.uncertainReason && <p className="notice notice--warning">{decision.uncertainReason}</p>}</div>)}
          </div>}
        </Panel>;
      })}</div>}
    </div>
  </>;
}

export function LiveReviewsWorkspace({ projectId, alertId }: { projectId: string; alertId?: string }) {
  const [data, setData] = useState<AssessmentResults | null>(null);
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [membership, setMembership] = useState<ProjectMembership | null>(null);
  const [busy, setBusy] = useState(false);
  const [analysisJob, setAnalysisJob] = useState<BackgroundJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try {
      const [next, member, sourceRows] = await Promise.all([getAssessmentResults(projectId), getCurrentProjectMembership(projectId), listSources(projectId)]);
      setData(next); setMembership(member); setSources(sourceRows); setError(null);
    } catch (value) { setError(errorText(value)); }
  }, [projectId]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  useEffect(() => {
    if (!analysisJob || !["queued", "running", "retrying"].includes(analysisJob.status)) return;
    const timer = window.setInterval(() => {
      void getJob(projectId, analysisJob.id).then((next) => {
        setAnalysisJob(next);
        if (next.status === "completed") void load();
      }).catch((value) => setError(errorText(value)));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [analysisJob, projectId, load]);
  async function assess() {
    setBusy(true); setError(null);
    try {
      const job = await submitAnalysisJob(projectId);
      setAnalysisJob(job);
      if (job.status === "completed") await load();
    }
    catch (value) { setError(errorText(value)); }
    finally { setBusy(false); }
  }
  async function retryAnalysis() {
    if (!analysisJob) return;
    setBusy(true); setError(null);
    try { setAnalysisJob(await retryJob(projectId, analysisJob)); }
    catch (value) { setError(errorText(value)); }
    finally { setBusy(false); }
  }
  const coverage = data?.latestRun?.coverage ?? [];
  const uncertainCount = coverage.filter((row) => row.state !== "assessed").length;
  const driftedTables = sources.filter((source) => source.status === "schema_drift");
  const reviewState = data?.alerts.length ? "Needs review" : !data?.latestRun ? "Ready to assess" : uncertainCount || driftedTables.length ? "Evidence unclear" : "No detected issue in assessed sources";
  return <>
    <PageHeading eyebrow="REVIEW QUEUE" title="Reviews" description="Check confirmed decisions against verified source facts." action={membership && membership.role !== "viewer" && <button className="button button--primary" disabled={busy} onClick={() => void assess()}>{busy ? "Running assessment…" : "Run assessment"}</button>} />
    {analysisJob && <p role="status" className="notice notice--info">Evidence analysis: {analysisJob.status}.
      {analysisJob.status === "failed" && <button className="button button--secondary" disabled={busy} onClick={() => void retryAnalysis()}>Retry analysis</button>}
    </p>}
    {alertId && <ImpactGraph key={`${projectId}/${alertId}`} projectId={projectId} alertId={alertId} />}
    {error && <p role="alert" className="notice notice--error">{error}</p>}
    {driftedTables.length > 0 && <p role="status" className="notice notice--warning">Coverage gap: {driftedTables.map((source) => source.name).join(", ")} {driftedTables.length === 1 ? "has" : "have"} a paused table mapping. Repair the header or column values and refresh the folder before relying on this assessment.</p>}
    <div className="review-summary workspace-card"><div><span className="section-kicker">LATEST ASSESSMENT</span><h2>{reviewState}</h2><p>{data?.latestRun ? `${data.latestRun.findingCount} ${data.latestRun.findingCount === 1 ? "finding" : "findings"} checked · ${data.latestRun.alertCount} ${data.latestRun.alertCount === 1 ? "alert" : "alerts"} · ${uncertainCount} ${uncertainCount === 1 ? "assumption" : "assumptions"} with incomplete coverage.` : "Run an assessment after you confirm decisions and extract source facts."}</p></div><span className="review-summary__symbol" aria-hidden="true">◇</span></div>
    {coverage.length > 0 && <Panel className="workspace-card coverage-panel"><span className="section-kicker">COVERAGE</span><h2>What the assessment checked</h2><div className="coverage-list">{coverage.map((row) => <div key={row.assumption_id} className="coverage-list__row"><StatusPill tone={row.state === "assessed" ? "success" : "warning"}>{row.state === "assessed" ? "Assessed" : "Evidence unclear"}</StatusPill><span>{row.reason}</span></div>)}</div></Panel>}
    <div className="workspace-section workspace-stack">{data?.alerts.length ? data.alerts.map((alert) => {
      const finding = data.findings.find((row) => row.id === alert.findingId);
      const evidenceUnavailable = finding ? [finding.baselineEvidence, finding.updateEvidence].some((evidence) => { const source = sources.find((row) => row.id === evidence.sourceId); return source && source.status !== "ready"; }) : false;
      const coverageState = coverage.find((row) => row.assumption_id === finding?.assumptionId)?.state;
      return <Panel key={alert.id} className="workspace-card review-item"><div className="source-item__head"><div><span className="section-kicker">DECISION ALERT</span><h2>Decision needs review</h2></div><StatusPill tone="warning">{alert.severity}</StatusPill></div>
        <div className="review-delta"><strong>{finding?.reasonCode === "DATE_AFTER_REQUIRED_BY" ? "Date moved past the target" : finding?.reasonCode?.replaceAll("_", " ") ?? "Source update"}</strong>{finding?.deltaDays != null && <span>{finding.deltaDays} days later</span>}</div>
        {finding && <p className="review-card__meta">Classification: {finding.classification} · {evidenceUnavailable ? "Evidence unclear: source access unavailable" : "Evidence: exact quote verified"} · Coverage: {coverageState ?? "unknown"}</p>}
        {finding && <div className="review-evidence">{[finding.baselineEvidence, finding.updateEvidence].map((evidence, index) => { const source = sources.find((row) => row.id === evidence.sourceId); return <EvidenceReference key={`${alert.id}-${index}`} evidence={evidence} label={index === 0 ? "ORIGINAL EVIDENCE" : "NEW EVIDENCE"} available={!source || source.status === "ready"} sourceType={source?.mime_type} />; })}</div>}
        <a className="text-link" href={`/projects/${encodeURIComponent(projectId)}/reviews?alertId=${encodeURIComponent(alert.id)}`}>View impact graph →</a>
        <ReviewActionPanel projectId={projectId} alertId={alert.id} reviewState={alert.reviewState} canReview={membership?.role === "admin" || membership?.role === "editor"} onSubmitted={load} />
      </Panel>;
    }) : <EmptyState title={reviewState} description={data?.latestRun ? uncertainCount ? "Some assumptions could not be assessed from the available evidence. Check coverage above before drawing a conclusion." : "The assessed sources did not contradict a monitored assumption in the latest run." : "Run an assessment after extracting facts from your connected sources."} />}</div>
  </>;
}
