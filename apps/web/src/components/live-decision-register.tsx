"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { PageHeading, Panel, StatusPill } from "@/components/ui";
import { WorkflowGuide } from "@/components/workflow-guide";
import {
  confirmLiveDecision, createLiveDecision, getCurrentProjectMembership, getSourceDetail,
  listLiveDecisions, listSources, retireLiveDecision,
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
  const [loading, setLoading] = useState(true);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const canEdit = membership !== null && membership.role !== "viewer";
  const currentDecisions = decisions.filter((row) => row.status !== "retired");
  const archivedDecisions = decisions.filter((row) => row.status === "retired");

  const load = useCallback(async () => {
    try {
      const [nextDecisions, nextSources, nextMember] = await Promise.all([
        listLiveDecisions(projectId), listSources(projectId), getCurrentProjectMembership(projectId),
      ]);
      setDecisions(nextDecisions); setSources(nextSources); setMembership(nextMember);
      setSourceId((current) => nextSources.some((row) => row.id === current) ? current : nextSources[0]?.id ?? "");
      setError(null);
    } catch (value) { setError(value instanceof Error ? value.message : "Could not load project decisions."); }
    finally { setLoading(false); }
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
    if (!source || source.id !== sourceId || !quote.trim() || !source.contentSnapshot.includes(quote.trim())) {
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
      setError("Choose the original required-by date."); return;
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
      setStatement(""); setAssumption(""); setQuote(""); setRationale("");
      await load();
    } catch (value) { setError(value instanceof Error ? value.message : "Could not create the decision draft."); }
    finally { setBusy(false); }
  }

  async function confirm(decision: LiveDecision) {
    setBusy(true); setError(null); setNotice(null);
    try { await confirmLiveDecision(projectId, decision); await load(); setNotice("Decision confirmed. Its assumption is ready for extraction and assessment."); }
    catch (value) { await load(); setError(value instanceof Error ? value.message : "Could not confirm the decision."); }
    finally { setBusy(false); }
  }

  async function remove(decision: LiveDecision) {
    setBusy(true); setError(null); setNotice(null);
    try {
      await retireLiveDecision(projectId, decision);
      setRemovingId(null);
      await load();
      setNotice(decision.status === "draft" ? "Draft discarded. Its record is available under Archived decisions." : "Decision archived. Its assumptions are no longer monitored. Previous assessment results remain as history.");
    } catch (value) {
      await load();
      setError(value instanceof Error ? value.message : "Could not archive the decision. Try again.");
    } finally { setBusy(false); }
  }

  return <>
    <PageHeading eyebrow="STEP 2 · ORIGINAL PLAN" title="Decision register" description="Your team's decisions, their reasons, and the assumptions to monitor. Confirm a draft to start checking it against updates." action={<Link className="button button--secondary" href={`/projects/${encodeURIComponent(projectId)}/sources`}>Next: extract updates →</Link>} />
    <WorkflowGuide projectId={projectId} current="decisions" />
    {error && <p role="alert" className="notice notice--error">{error}</p>}
    {notice && <p role="status" className="notice notice--success">{notice}</p>}
    <div className="workspace-section__heading"><div><span className="section-kicker">PROJECT RECORD</span><h2>Current decisions</h2></div><span className="section-count">{currentDecisions.filter((row) => row.status === "active").length} monitored · {currentDecisions.filter((row) => row.status === "draft").length} drafts</span></div>
    <div className="workspace-stack">{loading ? <p role="status">Loading decisions…</p> : currentDecisions.length === 0 ? <Panel className="empty-state"><div className="empty-state__mark" aria-hidden="true">◇</div><h2>No current decisions</h2><p>Create a draft below, then confirm it to start monitoring.</p></Panel> : currentDecisions.map((decision) => <Panel className="workspace-card decision-item" key={decision.id}>
      <div className="source-item__head"><div><span className="section-kicker">DECISION</span><h2>{decision.statement}</h2></div><StatusPill tone={decision.status === "active" ? "success" : "warning"}>{decision.status === "active" ? "Monitoring active" : "Draft · not monitored"}</StatusPill></div>
      <p className="supporting-copy">Owner: {decision.owner} · Revision {decision.activeRevision}</p>
      {decision.rationale && <p className="supporting-copy">Why: {decision.rationale}</p>}
      {decision.status === "draft" && <p className="notice notice--info">This draft is excluded from assessments. Confirm it when the original plan and deadline are correct.</p>}
      {canEdit && <div className="decision-actions">
        {decision.status === "draft" && <button className="button button--primary" disabled={busy} onClick={() => void confirm(decision)}>Confirm decision</button>}
        <button className="button button--secondary" disabled={busy} aria-expanded={removingId === decision.id} onClick={() => setRemovingId(removingId === decision.id ? null : decision.id)}>{decision.status === "draft" ? "Discard draft" : "Archive decision"}</button>
      </div>}
      {removingId === decision.id && <div className="decision-removal" role="group" aria-label={`Confirm removal of ${decision.statement}`}>
        <strong>{decision.status === "draft" ? "Discard this draft?" : "Archive this decision?"}</strong>
        <p>It will leave Current decisions and stop being monitored. The record and evidence are kept. You can find the decision under Archived decisions.</p>
        <div className="decision-actions"><button className="button button--secondary" disabled={busy} onClick={() => setRemovingId(null)}>Cancel</button><button className="button button--danger" disabled={busy} onClick={() => void remove(decision)}>{busy ? "Saving…" : decision.status === "draft" ? "Yes, discard draft" : "Yes, archive decision"}</button></div>
      </div>}
    </Panel>)}</div>
    {archivedDecisions.length > 0 && <div className="archived-decisions">
      <button className="button button--secondary" aria-expanded={showArchived} aria-controls="archived-decisions" onClick={() => setShowArchived(!showArchived)}>{showArchived ? "Hide" : "Show"} archived decisions ({archivedDecisions.length})</button>
      {showArchived && <div id="archived-decisions" className="workspace-stack"><p className="supporting-copy">These decisions are kept for reference and are excluded from new assessments.</p>{archivedDecisions.map((decision) => <Panel className="workspace-card" key={decision.id}><h3>{decision.statement}</h3><StatusPill>Archived · not monitored</StatusPill><p className="supporting-copy">Owner: {decision.owner} · Revision {decision.activeRevision}</p></Panel>)}</div>}
    </div>}
    {canEdit && <Panel className="workspace-card workspace-card--spaced"><div className="flow-card-heading"><span className="flow-step">+</span><div className="flow-card-heading__copy"><span className="section-kicker">NEW DECISION</span><h2>Create a decision draft</h2><p>Record what you decided before the update. The assessment will compare later facts against this original requirement.</p></div></div>
      {sources.length === 0 ? <p className="notice notice--warning"><Link className="text-link" href={`/projects/${encodeURIComponent(projectId)}/connections`}>Connect and refresh a Drive folder</Link> before creating a decision.</p> : <form onSubmit={(event) => { event.preventDefault(); void createDraft(); }}>
        <fieldset className="decision-form-section"><legend>1. Original evidence</legend>
        <p className="field-help">Choose the document with the original commitment, rather than the later delay notice.</p>
        <label className="form-field">Original evidence source<select className={inputClass} value={sourceId} onChange={(event) => { setSource(null); setQuote(""); setSourceId(event.target.value); }}>{sources.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
        {source?.id === sourceId && <div className="source-preview" aria-label="Source text"><span className="section-kicker">SOURCE TEXT</span><p>{source.contentSnapshot}</p></div>}
        <label className="form-field">Exact quote from source<textarea className={inputClass} value={quote} onChange={(event) => setQuote(event.target.value)} rows={2} /></label>
        <p className="field-help">Copy the source wording exactly. Date evidence should include the year, for example October 15, 2026.</p>
        </fieldset>
        <fieldset className="decision-form-section"><legend>2. Decision and reason</legend>
        <div className="form-grid form-grid--two">
          <label className="form-field">Decision statement<input className={inputClass} value={statement} onChange={(event) => setStatement(event.target.value)} /></label>
          <label className="form-field">Owner<input className={inputClass} value={owner} onChange={(event) => setOwner(event.target.value)} /></label>
        </div>
        <label className="form-field">Rationale<input className={inputClass} value={rationale} onChange={(event) => setRationale(event.target.value)} /></label>
        </fieldset>
        <fieldset className="decision-form-section"><legend>3. Requirement to monitor</legend>
        <p className="field-help">Keep the original deadline here. If delivery was required by October 15, an October 29 update should be compared against October 15.</p>
        <label className="form-field">Assumption to monitor<input className={inputClass} value={assumption} onChange={(event) => setAssumption(event.target.value)} placeholder="Vendor delivers by the launch deadline" /></label>
        <div className="form-grid form-grid--three">
          <label className="form-field">Entity ID<input className={inputClass} value={entityId} onChange={(event) => setEntityId(event.target.value)} placeholder="vendor_acme" /><span className="field-help">A stable name for the vendor or subject, using lowercase letters and underscores.</span></label>
          <label className="form-field">Predicate<input className={inputClass} value={predicate} onChange={(event) => setPredicate(event.target.value)} /><span className="field-help">What to track. Use delivery_date for a delivery deadline.</span></label>
          <label className="form-field">Originally required by<input className={inputClass} type="date" value={expectedDate} onChange={(event) => setExpectedDate(event.target.value)} /></label>
        </div>
        </fieldset>
        <button type="submit" className="button button--primary" disabled={busy || !source || source.id !== sourceId}>{busy ? "Saving…" : "Create draft"}</button>
      </form>}
    </Panel>}
  </>;
}
