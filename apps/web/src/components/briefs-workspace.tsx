"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { beginBriefExportAuthorization, createBrief, exportBrief, getAssessmentResults, getBrief, getBriefExport, getConnection, getCurrentProjectMembership, listBriefs } from "@/lib/api/client";
import type { AssessmentResults, BriefExport, BriefPreview } from "@/lib/api/client";
import { isDemoProject } from "@/lib/demo/use-project-data";
import { EmptyState, PageHeading, Panel } from "@/components/ui";

function errorMessage(value: unknown): string {
  return value instanceof Error ? value.message : "The request failed. Try again.";
}

export function BriefsWorkspace({ projectId }: { projectId: string }) {
  const router = useRouter();
  const [results, setResults] = useState<AssessmentResults | null>(null);
  const [briefs, setBriefs] = useState<BriefPreview[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [canCreate, setCanCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<{ signature: string; key: string } | null>(null);

  const load = useCallback(async () => {
    if (isDemoProject(projectId)) { setLoading(false); return; }
    setLoading(true);
    try {
      const [nextResults, nextBriefs, member] = await Promise.all([
        getAssessmentResults(projectId), listBriefs(projectId), getCurrentProjectMembership(projectId),
      ]);
      setResults(nextResults);
      setBriefs(nextBriefs);
      setCanCreate(member.role !== "viewer");
      setSelected(nextResults.alerts.filter((alert) => ["kept", "revised", "retired", "dismissed"].includes(alert.reviewState)).map((alert) => alert.id));
      setError(null);
    } catch (value) {
      setError(errorMessage(value));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function prepare() {
    const runId = results?.latestRun?.runId;
    if (!runId || selected.length === 0) return;
    const signature = JSON.stringify([runId, [...selected].sort()]);
    const key = pending?.signature === signature ? pending.key : crypto.randomUUID();
    setPending({ signature, key });
    setBusy(true);
    setError(null);
    try {
      const brief = await createBrief(projectId, runId, selected, key);
      setPending(null);
      router.push(`/projects/${encodeURIComponent(projectId)}/briefs/${encodeURIComponent(brief.id)}`);
    } catch (value) {
      setError(errorMessage(value));
    } finally {
      setBusy(false);
    }
  }

  const reviewed = results?.alerts.filter((alert) => ["kept", "revised", "retired", "dismissed"].includes(alert.reviewState)) ?? [];
  return <>
    <PageHeading eyebrow="DECISION SUMMARIES" title="Briefs" description="Prepare a fixed record from a completed assessment and human reviews." />
    {error && <p role="alert" className="notice notice--error">{error}</p>}
    {loading ? <p role="status">Loading briefs…</p> : isDemoProject(projectId) ?
      <EmptyState title="No live briefs in the demo fixture" description="Open a connected project to prepare a reviewed brief." /> : <>
      <Panel className="mb-6 space-y-4 p-6">
        <h2 className="text-lg font-semibold">Prepare a brief</h2>
        {!results?.latestRun ? <p>Run an assessment before preparing a brief.</p> : reviewed.length === 0 ?
          <p>Review an alert from this assessment before preparing a brief.</p> : <>
          <p className="text-sm text-slate-600">Assessment {results.latestRun.runId}. Select reviewed alerts to include.</p>
          <div className="space-y-2">{reviewed.map((alert) => <label className="flex items-center gap-3" key={alert.id}>
            <input type="checkbox" checked={selected.includes(alert.id)} disabled={busy || !canCreate}
              onChange={(event) => setSelected((current) => event.target.checked ? [...current, alert.id] : current.filter((id) => id !== alert.id))} />
            <span>{alert.severity} severity · {alert.reviewState} · {alert.id}</span>
          </label>)}</div>
          {canCreate && <button className="button button--primary" disabled={busy || selected.length === 0} onClick={() => void prepare()}>
            {busy ? "Preparing…" : pending ? "Retry preview" : "Create preview"}
          </button>}
        </>}
      </Panel>
      {briefs.length === 0 ? <EmptyState title="No briefs yet" description="A reviewed assessment can be saved as an immutable preview." /> :
        <div className="space-y-3">{briefs.map((brief) => <Panel className="p-5" key={brief.id}>
          <h2 className="font-semibold">{brief.items.length} reviewed {brief.items.length === 1 ? "alert" : "alerts"}</h2>
          <p className="text-sm text-slate-600">Created {new Date(brief.createdAt).toLocaleString()}</p>
          <a className="text-link" href={`/projects/${encodeURIComponent(projectId)}/briefs/${encodeURIComponent(brief.id)}`}>Open preview →</a>
        </Panel>)}</div>}
    </>}
  </>;
}

export function BriefDetailWorkspace({ projectId, briefId }: { projectId: string; briefId: string }) {
  const [brief, setBrief] = useState<BriefPreview | null>(null);
  const [exportResult, setExportResult] = useState<BriefExport | null>(null);
  const [exportAccess, setExportAccess] = useState(false);
  const [canConnectExport, setCanConnectExport] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    void Promise.all([getBrief(projectId, briefId), getBriefExport(projectId, briefId), getConnection(projectId), getCurrentProjectMembership(projectId)])
      .then(([nextBrief, nextExport, connection, member]) => { setBrief(nextBrief); setExportResult(nextExport); setExportAccess(connection.export_scope_granted); setCanConnectExport(member.role === "admin"); })
      .catch((value) => setError(errorMessage(value))).finally(() => setLoading(false));
  }, [projectId, briefId]);
  async function authorize() {
    setBusy(true); setError(null);
    try {
      const result = await beginBriefExportAuthorization(projectId);
      window.location.assign(result.authorization_url);
    } catch (value) { setError(errorMessage(value)); setBusy(false); }
  }
  async function runExport() {
    setBusy(true); setError(null);
    try { setExportResult(await exportBrief(projectId, briefId)); }
    catch (value) {
      setError(errorMessage(value));
      void getBriefExport(projectId, briefId).then(setExportResult);
    } finally { setBusy(false); }
  }
  return <>
    <PageHeading eyebrow="DECISION SUMMARIES" title="Brief preview" description="This content is fixed to the assessment and reviews shown below." />
    {loading ? <p role="status">Loading brief…</p> : !brief ? <EmptyState title="Brief could not be loaded" description={error ?? "This brief is unavailable."} /> : <>
      <Panel className="p-6"><pre className="whitespace-pre-wrap break-words font-sans text-sm leading-7">{brief.content}</pre></Panel>
      <Panel className="mt-5 space-y-3 p-6">
        <h2 className="text-lg font-semibold">Google Docs export</h2>
        <p className="text-sm text-slate-600">Export this fixed brief only after granting per-file Google Drive access.</p>
        {!exportAccess ? canConnectExport ? <button className="button button--primary" disabled={busy} onClick={() => void authorize()}>Connect Google Docs export</button> : <p>Ask a project administrator to connect Google Docs export.</p> :
          exportResult?.status === "completed" && exportResult.nativeUrl ?
            <a className="text-link" href={exportResult.nativeUrl} target="_blank" rel="noopener noreferrer">Open exported Google Doc ↗</a> :
            <button className="button button--primary" disabled={busy} onClick={() => void runExport()}>
              {busy ? "Exporting…" : exportResult?.status === "failed" ? "Retry export" : exportResult?.status === "in_progress" ? "Check or retry export" : "Export to Google Docs"}
            </button>}
        {exportResult?.status === "in_progress" && <p role="status">Export in progress. Check again here; if delivery stopped, retry becomes available after two minutes.</p>}
        {exportResult?.status === "failed" && <p role="status">The export failed. Retry will look for the same document.</p>}
      </Panel>
      {error && <p role="alert" className="notice notice--error">{error}</p>}
      <p className="mt-4 text-sm text-slate-600">Assessment {brief.runId} · Snapshot {brief.digest.slice(0, 12)}</p>
      <a className="text-link mt-4 inline-block" href={`/projects/${encodeURIComponent(projectId)}/briefs`}>← All briefs</a>
    </>}
  </>;
}
