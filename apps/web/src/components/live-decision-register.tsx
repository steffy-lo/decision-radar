"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { PageHeading, Panel, StatusPill } from "@/components/ui";
import {
  confirmLiveDecision, createLiveDecision, getCurrentProjectMembership, getSourceDetail,
  listLiveDecisions, listSources,
} from "@/lib/api/client";
import type { LiveDecision, ProjectMembership, SourceDetail, SourceSummary } from "@/lib/api/client";

const inputClass = "form-control";

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
    const missing = [
      ["Decision statement", statement], ["Owner", owner],
      ["Assumption to monitor", assumption], ["Entity ID", entityId], ["Predicate", predicate],
    ].filter(([, value]) => !value.trim()).map(([label]) => label);
    if (missing.length) {
      setError(`Complete these fields: ${missing.join(", ")}.`); return;
    }
    if (!/^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$/.test(entityId)) {
      setError("Entity ID must use lowercase letters, numbers, and underscores, starting with a letter."); return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(expectedDate)) {
      setError("Choose an expected date."); return;
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
    {error && <p role="alert" className="notice notice--error">{error}</p>}
    {notice && <p role="status" className="notice notice--success">{notice}</p>}
    <div className="workspace-section__heading"><div><span className="section-kicker">PROJECT RECORD</span><h2>Decisions</h2></div><span className="section-count">{decisions.length} total</span></div>
    <div className="workspace-stack">{decisions.length === 0 ? <Panel className="empty-state"><div className="empty-state__mark" aria-hidden="true">◇</div><h2>No decisions yet</h2><p>Create a draft below to start tracking a decision and its evidence.</p></Panel> : decisions.map((decision) => <Panel className="workspace-card decision-item" key={decision.id}>
      <div className="source-item__head"><div><span className="section-kicker">DECISION</span><h2>{decision.statement}</h2></div><StatusPill tone={decision.status === "active" ? "success" : "warning"}>{decision.status}</StatusPill></div>
      <p className="supporting-copy">Owner: {decision.owner} · Revision {decision.activeRevision}</p>
      {decision.status === "draft" && membership?.role !== "viewer" && <button className="button button--primary" disabled={busy} onClick={() => void confirm(decision)}>Confirm decision</button>}
    </Panel>)}</div>
    {membership?.role !== "viewer" && <Panel className="workspace-card workspace-card--spaced"><div className="flow-card-heading"><span className="flow-step">+</span><div className="flow-card-heading__copy"><span className="section-kicker">NEW DECISION</span><h2>Create a decision draft</h2><p>Start with a source quote, then add the decision and the date you need to track.</p></div></div>
      {sources.length === 0 ? <p className="notice notice--warning">Refresh a Drive folder on the Sources page first.</p> : <>
        <label className="form-field">Evidence source<select className={inputClass} value={sourceId} onChange={(event) => setSourceId(event.target.value)}>{sources.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
        {source && <div className="source-preview" aria-label="Source text"><span className="section-kicker">SOURCE TEXT</span><p>{source.contentSnapshot}</p></div>}
        <label className="form-field">Exact quote from source<textarea className={inputClass} value={quote} onChange={(event) => setQuote(event.target.value)} rows={2} /></label>
        <div className="form-grid form-grid--two">
          <label className="form-field">Decision statement<input className={inputClass} value={statement} onChange={(event) => setStatement(event.target.value)} /></label>
          <label className="form-field">Owner<input className={inputClass} value={owner} onChange={(event) => setOwner(event.target.value)} /></label>
        </div>
        <label className="form-field">Rationale<input className={inputClass} value={rationale} onChange={(event) => setRationale(event.target.value)} /></label>
        <label className="form-field">Assumption to monitor<input className={inputClass} value={assumption} onChange={(event) => setAssumption(event.target.value)} placeholder="Vendor delivers by the launch deadline" /></label>
        <div className="form-grid form-grid--three">
          <label className="form-field">Entity ID<input className={inputClass} value={entityId} onChange={(event) => setEntityId(event.target.value)} placeholder="vendor_acme" /></label>
          <label className="form-field">Predicate<input className={inputClass} value={predicate} onChange={(event) => setPredicate(event.target.value)} /></label>
          <label className="form-field">Expected by<input className={inputClass} type="date" value={expectedDate} onChange={(event) => setExpectedDate(event.target.value)} /></label>
        </div>
        <button className="button button--primary" disabled={busy} onClick={() => void createDraft()}>{busy ? "Saving…" : "Create draft"}</button>
      </>}
    </Panel>}
  </>;
}
