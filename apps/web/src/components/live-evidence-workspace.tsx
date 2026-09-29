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
import { PageHeading, Panel, StatusPill } from "@/components/ui";

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
    <PageHeading eyebrow="PROJECT EVIDENCE" title="Sources" description="Connect a Drive folder, refresh its files, then extract quote-backed facts." />
    <DriveConnectionPanel projectId={projectId} onSourcesChanged={() => void load()} />
    {error && <p role="alert" className="mt-4 rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
    <Panel className="mt-6 space-y-3">
      <h2>Extraction mapping</h2>
      <p className="text-sm text-slate-600">Map wording in the source to a confirmed decision assumption. Only verified, confirmed facts enter assessment.</p>
      <label className="block text-sm">Monitored assumption
        <select className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 p-2" value={selectedAssumption} onChange={(event) => setSelectedAssumption(event.target.value)}>
          {assumptions.length === 0 && <option value="">No active assumptions</option>}
          {assumptions.map((row) => <option key={row.id} value={row.id}>{row.decisionStatement}: {row.statement}</option>)}
        </select>
      </label>
      {selected && <p className="text-xs text-slate-600">Trusted entity: {selected.entityId} · predicate: {selected.predicate}</p>}
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">Entity wording in source<input className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 p-2" value={entityAlias} onChange={(event) => setEntityAlias(event.target.value)} placeholder="e.g. Acme Logistics" /></label>
        <label className="text-sm">Predicate wording in source<input className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 p-2" value={predicateAlias} onChange={(event) => setPredicateAlias(event.target.value)} placeholder="e.g. delivery date" /></label>
      </div>
      {assumptions.length === 0 && <p className="text-sm text-amber-300">Confirm a decision with a monitored assumption before extracting facts.</p>}
    </Panel>
    <div className="mt-6 space-y-4">
      <h2 className="text-xl font-semibold">Connected sources</h2>
      {loading ? <p>Loading sources…</p> : sources.length === 0 ? <p className="text-slate-600">No sources in the selected Drive folder yet.</p> : sources.map((source) => {
        const result = extractions[source.id];
        return <Panel className="space-y-3" key={source.id}>
          <div className="flex items-start justify-between gap-3"><div><h3 className="font-semibold">{source.name}</h3><a href={source.native_url} target="_blank" rel="noopener noreferrer" className="text-sm text-indigo-300 underline">Open source</a></div><StatusPill tone="success">{source.status}</StatusPill></div>
          {membership?.role !== "viewer" && <button className="button button--primary" disabled={busySource !== null || !selected} onClick={() => void runExtraction(source.id)}>{busySource === source.id ? "Extracting…" : "Extract with Gemini"}</button>}
          {result && <div className="space-y-3 border-t border-slate-700 pt-3"><p role="status" className="text-sm text-emerald-300">{result.publishedFactCount} verified facts published for assessment</p>
            {result.facts.map((fact, index) => <div key={`${source.id}-${index}`} className="rounded-lg bg-slate-900 p-3 text-sm text-slate-100"><strong>{fact.entity} · {fact.predicate}</strong><span className="ml-2 text-slate-300">{fact.state}</span><blockquote className="mt-2 border-l-2 border-indigo-400 pl-3">“{fact.quote}”</blockquote>{fact.uncertainReason && <p className="mt-1 text-amber-300">{fact.uncertainReason}</p>}</div>)}
            {result.decisions.map((decision, index) => <div key={`decision-${index}`} className="text-sm"><strong>Suggested decision:</strong> {decision.statement}{decision.uncertainReason && <span className="text-amber-300"> · {decision.uncertainReason}</span>}</div>)}
          </div>}
        </Panel>;
      })}
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
    <PageHeading eyebrow="REVIEW QUEUE" title="Reviews" description="Run deterministic checks against confirmed decisions and verified source facts." />
    {membership?.role !== "viewer" && <button className="button button--primary" disabled={busy} onClick={() => void assess()}>{busy ? "Running assessment…" : "Run assessment"}</button>}
    {error && <p role="alert" className="mt-4 text-red-300">{error}</p>}
    {data?.latestRun && <p role="status" className="mt-4 text-sm text-slate-700">Latest run: {data.latestRun.findingCount} findings, {data.latestRun.alertCount} alerts.</p>}
    <div className="mt-6 space-y-4">{data?.alerts.length ? data.alerts.map((alert) => {
      const finding = data.findings.find((row) => row.id === alert.findingId);
      return <Panel key={alert.id} className="space-y-3"><div className="flex justify-between"><h2 className="font-semibold">Decision needs review</h2><StatusPill tone="warning">{alert.severity}</StatusPill></div>
        <p className="text-sm">{finding?.reasonCode} {finding?.deltaDays != null && `· ${finding.deltaDays} days later`}</p>
        {finding && <div className="grid gap-3 sm:grid-cols-2"><blockquote className="border-l-2 border-slate-500 pl-3 text-sm">“{finding.baselineEvidence.quote}”</blockquote><blockquote className="border-l-2 border-amber-400 pl-3 text-sm">“{finding.updateEvidence.quote}”</blockquote></div>}
      </Panel>;
    }) : <p className="text-slate-600">No alerts yet. Run an assessment after extracting source facts.</p>}</div>
  </>;
}
