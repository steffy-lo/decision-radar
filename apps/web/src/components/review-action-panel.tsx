"use client";

import { useCallback, useEffect, useState } from "react";
import { getReviewHistory, submitAlertReview } from "@/lib/api/client";
import type { ReviewAction, ReviewHistory } from "@/lib/api/client";

const ACTIONS: { value: ReviewAction; label: string }[] = [
  { value: "keep", label: "Keep decision" },
  { value: "revise", label: "Revise decision" },
  { value: "retire", label: "Retire decision" },
  { value: "dismiss", label: "Dismiss alert" },
  { value: "request_clarification", label: "Request clarification" },
];

function label(action: ReviewAction): string {
  return ACTIONS.find((item) => item.value === action)?.label ?? action;
}

export function ReviewActionPanel({ projectId, alertId, reviewState, canReview, onSubmitted }: {
  projectId: string;
  alertId: string;
  reviewState: string;
  canReview: boolean;
  onSubmitted: () => Promise<void>;
}) {
  const [history, setHistory] = useState<ReviewHistory | null>(null);
  const [action, setAction] = useState<ReviewAction>("keep");
  const [rationale, setRationale] = useState("");
  const [statement, setStatement] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const load = useCallback(async () => {
    const next = await getReviewHistory(projectId, alertId);
    setHistory(next);
    setStatement((current) => current || next.decision.statement);
  }, [projectId, alertId]);

  useEffect(() => {
    void Promise.resolve().then(load).catch((value: unknown) => setError(value instanceof Error ? value.message : "Review history could not be loaded."));
  }, [load]);

  async function submit() {
    if (!history || !rationale.trim() || (action === "revise" && !statement.trim())) {
      setError("Add a rationale and, for Revise, a decision statement.");
      return;
    }
    setBusy(true); setError(null); setSaved(false);
    try {
      await submitAlertReview(projectId, alertId, history.decision.version, action, rationale.trim(), statement.trim());
      setRationale(""); setSaved(true);
      await Promise.all([load(), onSubmitted()]);
    } catch (value) {
      setError(value instanceof Error ? value.message : "Review could not be saved. Reload and try again.");
      await Promise.allSettled([load(), onSubmitted()]);
    } finally { setBusy(false); }
  }

  const revisions = new Map(history?.revisions.map((row) => [row.revision, row.statement]) ?? []);
  const editable = reviewState === "open" || reviewState === "clarification_requested";
  return <div className="review-actions">
    {history && <p className="review-card__meta">Decision: {history.decision.statement} · revision {history.decision.activeRevision}</p>}
    {canReview && editable && <div className="review-actions__form">
      <label className="form-field">Action
        <select className="form-control" value={action} onChange={(event) => setAction(event.target.value as ReviewAction)}>
          {ACTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
        </select>
      </label>
      {action === "revise" && <label className="form-field">Revised decision statement
        <input className="form-control" value={statement} onChange={(event) => setStatement(event.target.value)} />
      </label>}
      <label className="form-field">Rationale
        <textarea className="form-control" rows={3} value={rationale} onChange={(event) => setRationale(event.target.value)} placeholder="Explain why this action fits the evidence." />
      </label>
      <button className="button button--primary" type="button" disabled={busy || !history} onClick={() => void submit()}>{busy ? "Saving review…" : "Submit review"}</button>
    </div>}
    {error && <p role="alert" className="notice notice--error">{error}</p>}
    {saved && <p role="status" className="notice notice--success">Review saved.</p>}
    <div className="review-actions__history">
      <strong>Audit history</strong>
      {history?.reviews.length ? <ul>{history.reviews.map((review) => <li key={review.id}>
        <strong>{label(review.action)}</strong> by {review.actorId}: {review.rationale}
        {review.beforeRevision != null && review.afterRevision != null && <p>Before r{review.beforeRevision}: {revisions.get(review.beforeRevision) ?? "Unavailable"} · After r{review.afterRevision}: {revisions.get(review.afterRevision) ?? "Unavailable"}</p>}
      </li>)}</ul> : <p>No reviews recorded yet.</p>}
    </div>
  </div>;
}
