"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { HelpTooltip } from "@/components/help-tooltip";
import { extractionBlocker, extractionHelp } from "@/lib/domain/extraction-guidance";
import { WorkflowGuide } from "@/components/workflow-guide";
import { assessmentStatus } from "@/lib/domain/assessment-status";
import { DriveConnectionPanel } from "@/components/connections/drive-connection-panel";
import { EvidenceReference } from "@/components/evidence-reference";
import { ImpactGraph } from "@/components/graph/impact-graph";
import { ReviewActionPanel } from "@/components/review-action-panel";
import { TableMappingForm } from "@/components/table-mapping-form";
import {
  extractSource, getAssessmentReadiness, getAssessmentResults, getCurrentProjectMembership, getExtraction,
  getJob, getSourceDetail, listMonitoredAssumptions, listSources, retryJob, submitAnalysisJob,
} from "@/lib/api/client";
import type {
  AssessmentReadiness, AssessmentResults, BackgroundJob, ExtractionResult, MonitoredAssumption, ProjectMembership, SourceSummary,
} from "@/lib/api/client";
import { EmptyState, PageHeading, Panel, StatusPill } from "@/components/ui";

function errorText(value: unknown): string {
  return value instanceof Error ? value.message : "The request failed. Please try again.";
}

function countLabel(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

function isTable(mimeType: string): boolean {
  return ["application/vnd.google-apps.spreadsheet", "text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"].includes(mimeType);
}

export function LiveSourcesWorkspace({ projectId }: { projectId: string }) {
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [assumptions, setAssumptions] = useState<MonitoredAssumption[]>([]);
  const [selectedAssumption, setSelectedAssumption] = useState("");
  const [selectedSource, setSelectedSource] = useState("");
  const [sourcePreview, setSourcePreview] = useState("");
  const [previewError, setPreviewError] = useState(false);
  const [previewAttempt, setPreviewAttempt] = useState(0);
  const [completedSource, setCompletedSource] = useState<string | null>(null);
  const [entityAlias, setEntityAlias] = useState("");
  const [predicateAlias, setPredicateAlias] = useState("");
  const [extractions, setExtractions] = useState<Record<string, ExtractionResult>>({});
  const [busySource, setBusySource] = useState<string | null>(null);
  const [membership, setMembership] = useState<ProjectMembership | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setCompletedSource(null);
    try {
      const [nextSources, nextAssumptions, nextMembership] = await Promise.all([
        listSources(projectId), listMonitoredAssumptions(projectId), getCurrentProjectMembership(projectId),
      ]);
      setSources(nextSources);
      setAssumptions(nextAssumptions);
      setMembership(nextMembership);
      setSelectedAssumption((current) => nextAssumptions.some((row) => row.id === current) ? current : "");
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
  const updateSources = sources.filter((source) => !isTable(source.mime_type));
  const update = updateSources.find((source) => source.id === selectedSource);
  const blocker = extractionBlocker({ loading, role: membership?.role, assumption: Boolean(selected),
    source: update, subject: entityAlias, detail: predicateAlias, busy: busySource !== null });

  useEffect(() => {
    let cancelled = false;
    void Promise.resolve().then(async () => {
      if (cancelled) return;
      setSourcePreview(""); setPreviewError(false);
      if (!selectedSource) return;
      try {
        const detail = await getSourceDetail(projectId, selectedSource);
        if (!cancelled) setSourcePreview(detail.contentSnapshot);
      } catch { if (!cancelled) setPreviewError(true); }
    });
    return () => { cancelled = true; };
  }, [projectId, selectedSource, update?.updated_at, previewAttempt]);

  async function runExtraction() {
    if (blocker || !selected || !update) return;
    setBusySource(update.id); setCompletedSource(null); setError(null);
    try {
      const result = await extractSource(projectId, update.id, selected.id, entityAlias.trim(), predicateAlias.trim());
      setExtractions((current) => ({ ...current, [update.id]: result }));
      setCompletedSource(update.id);
    } catch (value) {
      setError(errorText(value));
    } finally { setBusySource(null); }
  }

  return <>
    <PageHeading eyebrow="STEP 3 · UPDATED EVIDENCE" title="Sources" description="Extract facts from the update document so they can be compared with your original requirement. Refresh Drive again whenever a document changes." action={<Link className="button button--secondary" href={`/projects/${encodeURIComponent(projectId)}/reviews`}>Next: check for conflicts →</Link>} />
    <WorkflowGuide projectId={projectId} current="sources" />
    <details className="source-connection-settings"><summary>Refresh files or manage the Drive connection</summary>
      <DriveConnectionPanel projectId={projectId} onSourcesChanged={() => void load()} />
      <p><Link className="text-link" href={`/projects/${encodeURIComponent(projectId)}/connections`}>Manage Meet connections and source monitoring →</Link></p>
    </details>
    {error && <p role="alert" className="notice notice--error">{error}</p>}
    <Panel className="workspace-card workspace-card--spaced">
      <div className="flow-card-heading"><div className="flow-card-heading__copy"><span className="section-kicker">FACT EXTRACTION</span><h2>Turn an update into facts</h2><p>Choose what to check and which document contains the update. Gemini reads it and saves facts supported by a direct quote. Then run an assessment in Reviews to check for conflicts.</p></div></div>
      <form className="extraction-form" onSubmit={(event) => { event.preventDefault(); void runExtraction(); }}>
        <div className="form-grid form-grid--two">
          <div><div className="field-label-row"><label className="form-field" htmlFor="extraction-requirement">Requirement to check</label><HelpTooltip label="Requirement to check">Choose an expectation your confirmed decision relies on, such as a delivery deadline. Draft decisions must be confirmed first.</HelpTooltip></div>
            <select id="extraction-requirement" className="form-control" value={selectedAssumption} disabled={busySource !== null} onChange={(event) => { setSelectedAssumption(event.target.value); setCompletedSource(null); }}>
              <option value="">Choose a requirement…</option>
              {assumptions.map((row) => <option key={row.id} value={row.id}>{row.statement}</option>)}
            </select>
            {selected && <p className="field-help">From your decision: {selected.decisionStatement}</p>}
          </div>
          <div><div className="field-label-row"><label className="form-field" htmlFor="extraction-source">Update document</label><HelpTooltip label="Update document">Choose the document with the latest information, rather than the original decision record. Refresh Drive first if the document has changed.</HelpTooltip></div>
            <select id="extraction-source" className="form-control" value={selectedSource} disabled={busySource !== null} onChange={(event) => { setSelectedSource(event.target.value); setCompletedSource(null); }}>
              <option value="">Choose an update…</option>
              {updateSources.map((source) => <option key={source.id} value={source.id}>{source.name}{source.monitoring_paused ? " (monitoring paused)" : source.status !== "ready" ? " (not ready)" : ""}</option>)}
            </select>
            <p className="field-help">Spreadsheets use column mapping in Connected sources below.</p>
          </div>
        </div>
        {update && <details className="extraction-preview" key={update.id}><summary>Read the saved copy of {update.name}</summary>
          <p className="field-help">This is the copy Gemini will read. If it is out of date, refresh Drive above.</p>
          {previewError ? <p role="status">The saved copy could not be loaded. <button type="button" className="button button--secondary" onClick={() => setPreviewAttempt((current) => current + 1)}>Try loading again</button></p> : <pre>{sourcePreview || "Loading saved copy…"}</pre>}
        </details>}
        <div className="form-grid form-grid--two">
          <div><div className="field-label-row"><label className="form-field" htmlFor="extraction-subject">Who or what is the update about?</label><HelpTooltip label="Who or what is the update about?">Copy the name used in the update, such as Acme Logistics. This helps match the update to the requirement you selected.</HelpTooltip></div>
            <input id="extraction-subject" className="form-control" maxLength={120} disabled={busySource !== null} value={entityAlias} onChange={(event) => { setEntityAlias(event.target.value); setCompletedSource(null); }} placeholder="e.g. Acme Logistics" />
            <p className="field-help">Use the name as it appears in the update.</p>
          </div>
          <div><div className="field-label-row"><label className="form-field" htmlFor="extraction-detail">What information should Gemini look for?</label><HelpTooltip label="What information should Gemini look for?">Use a short description from the update, such as delivery date. You do not need to enter the new date itself; Gemini finds it in the document.</HelpTooltip></div>
            <input id="extraction-detail" className="form-control" maxLength={120} disabled={busySource !== null} value={predicateAlias} onChange={(event) => { setPredicateAlias(event.target.value); setCompletedSource(null); }} placeholder="e.g. delivery date" />
            <p className="field-help">Describe the information, rather than its new value.</p>
          </div>
        </div>
        <p className="field-help">For a date, the document must include the year, for example October 24, 2026. Unclear information stays out of the comparison until it can be verified.</p>
        <div className="extraction-action"><button type="submit" className="button button--primary" disabled={Boolean(blocker)} aria-describedby="extraction-readiness">{busySource ? "Reading update with Gemini…" : "Extract facts with Gemini"}</button>
          <p id="extraction-readiness" role="status">{blocker ?? "Ready. Gemini will read the selected update and check the supporting quote."}</p>
        </div>
      </form>
      {completedSource && <p role="status" className={`notice ${extractions[completedSource]?.publishedFactCount ? "notice--success" : "notice--warning"}`}>{extractions[completedSource]?.publishedFactCount ? "Facts saved." : "No facts are ready to compare yet."} <a className="text-link" href={`#source-${completedSource}`}>See the results and next steps below ↓</a></p>}
      {!loading && assumptions.length === 0 && <p className="notice notice--warning"><Link className="text-link" href={`/projects/${encodeURIComponent(projectId)}/decisions`}>Confirm a decision with a requirement to monitor</Link> before extracting facts. Drafts do not appear in this list.</p>}

    </Panel>
    <div className="workspace-section">
      <div className="workspace-section__heading"><div><span className="section-kicker">SOURCE LIBRARY</span><h2>Connected sources</h2></div><span className="section-count">{sources.length} files</span></div>
      {loading ? <p className="supporting-copy">Loading sources…</p> : sources.length === 0 ? <EmptyState title="No sources yet" description="Connect Drive and refresh a folder to bring its files into this project." /> : <div className="workspace-stack">{sources.map((source) => {
        const result = extractions[source.id];
        return <Panel className="workspace-card source-item" key={source.id}>
          <div className="source-item__head"><div><h3 id={`source-${source.id}`} className="source-anchor">{source.name}</h3><a href={source.native_url} target="_blank" rel="noopener noreferrer" className="text-link">Open source ↗</a></div><StatusPill tone={source.status === "ready" && !source.monitoring_paused ? "success" : "warning"}>{source.monitoring_paused ? "Monitoring paused" : source.failure_reason === "removed_from_folder" ? "Removed from folder" : source.status === "ready" ? "Ready" : source.status === "mapping_required" ? "Choose table columns" : source.status === "schema_drift" ? "Table columns changed" : "Needs attention"}</StatusPill></div>
          {source.failure_reason && <p role="status" className="notice notice--warning">{source.failure_reason === "removed_from_folder" ? "This file is no longer in the monitored folder. Add it back and refresh Drive to use it again." : "This file could not be read. Check that the connected Drive account can open it, then refresh Drive to try again."}</p>}
          {membership?.role === "admin" && isTable(source.mime_type) && <TableMappingForm projectId={projectId} source={source} onSaved={load} />}

          {result && (source.status !== "ready" || source.monitoring_paused) && <p role="status" className="notice notice--warning">{result.publishedFactCount} previously verified facts are paused until this source is ready and monitoring resumes.</p>}
          {!result && !isTable(source.mime_type) && <p className="field-help">No extraction results yet. To check this document, choose it in Update document above.</p>}
          {result && source.status === "ready" && !source.monitoring_paused && <div className="source-item__results">
            <h4>Latest extraction from this document</h4>
            <p className="field-help">Requirement checked: {assumptions.find((row) => row.id === result.assumptionId)?.statement ?? "A previously selected requirement, which is no longer active."}</p>
            <p className={`notice ${result.publishedFactCount ? "notice--success" : "notice--warning"}`}>{result.publishedFactCount ? `${countLabel(result.publishedFactCount, "verified fact")} ready to compare. Open Reviews and run an assessment to check for conflicts.` : "No facts ready to compare. Read the guidance below, adjust the matching phrases or update the document, then extract again."}</p>
            {result.facts.map((fact, index) => <div key={`${source.id}-${index}`} className="fact-card"><div><strong>What the update says</strong><StatusPill>{fact.state === "ready" ? "Verified" : fact.state === "negated" ? "Confirmed as not happening" : "Needs clarification"}</StatusPill></div><blockquote>“{fact.quote}”</blockquote>{fact.uncertainReason && <p className="notice notice--warning">{extractionHelp(fact.uncertainReason)}</p>}</div>)}
            {result.facts.length === 0 && <p className="field-help">Gemini did not find a matching fact with a supporting quote. Check that you chose the update document and copied the correct name and description.</p>}
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
  const [readiness, setReadiness] = useState<AssessmentReadiness | null>(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    try {
      const [next, member, sourceRows, ready] = await Promise.all([getAssessmentResults(projectId), getCurrentProjectMembership(projectId), listSources(projectId), getAssessmentReadiness(projectId)]);
      setData(next); setMembership(member); setSources(sourceRows); setReadiness(ready); setError(null);
    } catch (value) { setReadiness(null); setError(errorText(value)); }
    finally { setLoading(false); }
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
  const status = assessmentStatus(data?.latestRun ?? null, data?.alerts.length ?? 0, driftedTables.length > 0);
  const jobPending = analysisJob !== null && ["queued", "running", "retrying"].includes(analysisJob.status);
  const stale = Boolean(data?.latestRun && readiness && data.latestRun.runId !== readiness.fingerprint);
  return <>
    <PageHeading eyebrow="STEP 4 · ASSESS AND REVIEW" title="Reviews" description="Check whether updated facts challenge your confirmed decisions. Review the evidence here and record your response; an assessment does not change your decisions." action={membership && membership.role !== "viewer" && <button className="button button--primary" disabled={busy || jobPending || !readiness?.canAssess} aria-describedby="assessment-readiness" onClick={() => void assess()}>{busy || jobPending ? "Running assessment…" : "Run assessment"}</button>} />
    <WorkflowGuide projectId={projectId} current="reviews" />
    <Panel className="workspace-card readiness-panel">
      <div id="assessment-readiness"><span className="section-kicker">BEFORE YOU RUN</span><h2>{loading ? "Checking what is ready…" : readiness?.title ?? "Readiness could not be checked"}</h2><p>{readiness?.reason ?? "Load the latest project inputs before running an assessment."}</p></div>
      {readiness && <p className="readiness-counts">{countLabel(readiness.activeDecisionCount, "active decision")} · {countLabel(readiness.draftDecisionCount, "draft")} excluded · {countLabel(readiness.assumptionCount, "monitored assumption")} · {readiness.comparableAssumptionCount} ready to compare</p>}
      {readiness && !readiness.canAssess && <Link className="button button--secondary" href={`/projects/${encodeURIComponent(projectId)}/${readiness.nextStep}`}>{readiness.nextStep === "decisions" ? "Go to Decisions" : "Go to Sources"} →</Link>}
      {!readiness && !loading && <button className="button button--secondary" onClick={() => void load()}>Try loading again</button>}
    </Panel>
    {analysisJob && <p role="status" className="notice notice--info">Evidence analysis: {analysisJob.status}.
      {analysisJob.status === "failed" && <button className="button button--secondary" disabled={busy} onClick={() => void retryAnalysis()}>Retry analysis</button>}
    </p>}
    {alertId && <ImpactGraph key={`${projectId}/${alertId}`} projectId={projectId} alertId={alertId} severity={data?.alerts.find((alert) => alert.id === alertId)?.severity} />}
    {error && <p role="alert" className="notice notice--error">{error}</p>}
    {stale && <p role="status" className="notice notice--warning">Project inputs have changed since this result. The result below is from the previous assessment. Complete any missing steps above, then run a new assessment.</p>}
    {driftedTables.length > 0 && <p role="status" className="notice notice--warning">Coverage gap: {driftedTables.map((source) => source.name).join(", ")} {driftedTables.length === 1 ? "has" : "have"} a paused table mapping. Repair the header or column values and refresh the folder before relying on this assessment.</p>}
    <div className="review-summary workspace-card"><div><span className="section-kicker">{stale ? "PREVIOUS ASSESSMENT" : "LATEST ASSESSMENT"}</span><h2>{status.title}</h2><p>{status.description}</p>{data?.latestRun && <p>{countLabel(data.latestRun.findingCount, "comparison")} · {countLabel(data.latestRun.alertCount, "alert")} · {countLabel(uncertainCount, "assumption")} with incomplete coverage.</p>}</div><span className="review-summary__symbol" aria-hidden="true">◇</span></div>
    {coverage.length > 0 && <Panel className="workspace-card coverage-panel"><span className="section-kicker">COVERAGE</span><h2>What the assessment checked</h2><div className="coverage-list">{coverage.map((row) => <div key={row.assumption_id} className="coverage-list__row"><StatusPill tone={row.state === "assessed" ? "success" : "warning"}>{row.state === "assessed" ? "Assessed" : "Evidence unclear"}</StatusPill><span>{row.reason === "No fact has the monitored predicate." ? "No verified update matches this requirement yet. Extract a relevant update in Sources, then run the assessment again." : row.reason === "Only uncertain or unlinked evidence was available." ? "The available update could not be confidently matched. Check the extraction guidance in Sources, then try again." : row.reason}</span></div>)}</div></Panel>}
    <div className="workspace-section workspace-stack">{data?.alerts.length ? data.alerts.map((alert) => {
      const finding = data.findings.find((row) => row.id === alert.findingId);
      const evidenceUnavailable = finding ? [finding.baselineEvidence, finding.updateEvidence].some((evidence) => { const source = sources.find((row) => row.id === evidence.sourceId); return source && source.status !== "ready"; }) : false;
      const coverageState = coverage.find((row) => row.assumption_id === finding?.assumptionId)?.state;
      return <Panel key={alert.id} className="workspace-card review-item"><div className="source-item__head"><div><span className="section-kicker">DECISION ALERT</span><h2>Decision needs review</h2></div><StatusPill tone="warning">{alert.severity}</StatusPill></div>
        <div className="review-delta"><strong>{finding?.reasonCode === "DATE_AFTER_REQUIRED_BY" ? "Date moved past the target" : finding?.reasonCode?.replaceAll("_", " ") ?? "Source update"}</strong>{finding?.deltaDays != null && <span>{finding.deltaDays} days later</span>}</div>
        {finding && <p className="review-card__meta">{finding.classification === "contradicts" ? "The update conflicts with this requirement." : "The update was compared with this requirement."} {evidenceUnavailable ? "The source is currently unavailable; check its access before relying on this result." : "The supporting quotes were verified."} {coverageState !== "assessed" && "Some evidence still needs clarification."}</p>}
        {finding && <div className="review-evidence">{[finding.baselineEvidence, finding.updateEvidence].map((evidence, index) => { const source = sources.find((row) => row.id === evidence.sourceId); return <EvidenceReference key={`${alert.id}-${index}`} evidence={evidence} label={index === 0 ? "ORIGINAL EVIDENCE" : "NEW EVIDENCE"} available={!source || source.status === "ready"} sourceType={source?.mime_type} />; })}</div>}
        <a className="text-link" href={`/projects/${encodeURIComponent(projectId)}/reviews?alertId=${encodeURIComponent(alert.id)}`}>View impact graph →</a>
        <ReviewActionPanel projectId={projectId} alertId={alert.id} reviewState={alert.reviewState} canReview={membership?.role === "admin" || membership?.role === "editor"} onSubmitted={load} />
      </Panel>;
    }) : null}</div>
  </>;
}
