"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { PageHeading, Panel, StatusPill } from "@/components/ui";
import {
  confirmLiveDecision, createLiveDecision, getCurrentProjectMembership, getSourceDetail,
  listLiveDecisions, listSources,
} from "@/lib/api/client";
import type { LiveDecision, ProjectMembership, SourceDetail, SourceSummary } from "@/lib/api/client";

const inputClass = "mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 p-2 text-slate-100";

export function LiveDecisionRegister({ projectId }: { projectId: string }) {
  const [decisions, setDecisions] = useState<LiveDecision[]>([]);
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [source, setSource] = useState<SourceDetail | null>(null);
  const [membership, setMembership] = useState<ProjectMembership | null>(null);
  const [statement, setStatement] = useState("");
  const [owner, setOwner] = useState("");
  const [rationale, setRationale] = useState("");
  const [assumption, setAssumption] = useState("");
  const [entityId, setEntityId] = useState("");
  const [predicate, setPredicate] = useState("delivery_date");
  const [expectedDate, setExpectedDate] = useState("");
  const [quote, setQuote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [nextDecisions, nextSources, nextMember] = await Promise.all([
        listLiveDecisions(projectId), listSources(projectId), getCurrentProjectMembership(projectId),
      ]);
      setDecisions(nextDecisions); setSources(nextSources); setMembership(nextMember);
      setSourceId((current) => nextSources.some((row) => row.id === current) ? current : nextSources[0]?.id ?? "");
      setError(null);
    } catch (value) { setError(value instanceof Error ? value.message : "Could not load project decisions."); }
  }, [projectId]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  useEffect(() => {
    if (!sourceId) return;
    let active = true;
    getSourceDetail(projectId, sourceId).then((value) => { if (active) setSource(value); })
      .catch((value: unknown) => { if (active) setError(value instanceof Error ? value.message : "Could not load source text."); });
    return () => { active = false; };
  }, [projectId, sourceId]);

  async function createDraft() {
    if (!source || !quote.trim() || !source.contentSnapshot.includes(quote.trim())) {
      setError("Paste one exact quote from the selected source text."); return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(expectedDate)) {
      setError("Enter an expected date in YYYY-MM-DD format."); return;
    }
    setBusy(true); setError(null); setNotice(null);
    const evidence = { sourceId: source.id, sourceTitle: source.name, nativeUrl: source.nativeUrl, quote: quote.trim() };
    try {
      await createLiveDecision(projectId, {
        statement, owner, rationale, evidence,
        assumptions: [{ statement: assumption, entityId, predicate, operator: "on_or_before",
          expectedValue: { type: "date", value: expectedDate }, criticality: "medium", evidence }],
      });
      setNotice("Decision draft created. Confirm it when the evidence and deadline are correct.");
      await load();
    } catch (value) { setError(value instanceof Error ? value.message : "Could not create the decision draft."); }
    finally { setBusy(false); }
  }

  async function confirm(decision: LiveDecision) {
    setBusy(true); setError(null); setNotice(null);
    try { await confirmLiveDecision(projectId, decision); await load(); setNotice("Decision confirmed. Its assumption is ready for extraction and assessment."); }
    catch (value) { setError(value instanceof Error ? value.message : "Could not confirm the decision."); }
    finally { setBusy(false); }
  }

  return <>
    <PageHeading eyebrow="DECISION INTELLIGENCE" title="Decision register" description="Create a quote-backed decision and confirm the date you want to monitor." action={<Link className="button button--secondary" href={`/projects/${encodeURIComponent(projectId)}/reviews`}>View reviews</Link>} />
    {error && <p role="alert" className="mb-4 rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
    {notice && <p role="status" className="mb-4 rounded-lg border border-emerald-800 bg-emerald-950/40 p-3 text-sm text-emerald-300">{notice}</p>}
    <div className="space-y-4">{decisions.length === 0 ? <p className="text-slate-600">No decisions yet.</p> : decisions.map((decision) => <Panel className="space-y-2" key={decision.id}>
      <div className="flex items-start justify-between gap-3"><h2 className="font-semibold">{decision.statement}</h2><StatusPill tone={decision.status === "active" ? "success" : "warning"}>{decision.status}</StatusPill></div>
      <p className="text-sm text-slate-600">Owner: {decision.owner} · Revision {decision.activeRevision}</p>
      {decision.status === "draft" && membership?.role !== "viewer" && <button className="button button--primary" disabled={busy} onClick={() => void confirm(decision)}>Confirm decision</button>}
    </Panel>)}</div>
    {membership?.role !== "viewer" && <Panel className="mt-8 space-y-4"><h2 className="text-lg font-semibold">New decision draft</h2>
      {sources.length === 0 ? <p className="text-sm text-amber-300">Refresh a Drive folder on the Sources page first.</p> : <>
        <label className="block text-sm">Evidence source<select className={inputClass} value={sourceId} onChange={(event) => setSourceId(event.target.value)}>{sources.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
        {source && <div className="max-h-48 overflow-auto rounded-lg bg-slate-900 p-3 text-xs whitespace-pre-wrap text-slate-200" aria-label="Source text">{source.contentSnapshot}</div>}
        <label className="block text-sm">Exact quote from source<textarea className={inputClass} value={quote} onChange={(event) => setQuote(event.target.value)} rows={2} /></label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm">Decision statement<input className={inputClass} value={statement} onChange={(event) => setStatement(event.target.value)} /></label>
          <label className="text-sm">Owner<input className={inputClass} value={owner} onChange={(event) => setOwner(event.target.value)} /></label>
        </div>
        <label className="block text-sm">Rationale<input className={inputClass} value={rationale} onChange={(event) => setRationale(event.target.value)} /></label>
        <label className="block text-sm">Assumption to monitor<input className={inputClass} value={assumption} onChange={(event) => setAssumption(event.target.value)} placeholder="Vendor delivers by the launch deadline" /></label>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm">Entity ID<input className={inputClass} value={entityId} onChange={(event) => setEntityId(event.target.value)} placeholder="vendor_acme" /></label>
          <label className="text-sm">Predicate<input className={inputClass} value={predicate} onChange={(event) => setPredicate(event.target.value)} /></label>
          <label className="text-sm">Expected by<input className={inputClass} type="date" value={expectedDate} onChange={(event) => setExpectedDate(event.target.value)} /></label>
        </div>
        <button className="button button--primary" disabled={busy} onClick={() => void createDraft()}>{busy ? "Saving…" : "Create draft"}</button>
      </>}
    </Panel>}
  </>;
}
