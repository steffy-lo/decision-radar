"use client";

import { useCallback, useEffect, useState } from "react";
import { Panel, StatusPill } from "@/components/ui";
import { getCurrentProjectMembership, getJob, getJobs, retryJob } from "@/lib/api/client";
import type { BackgroundJob, ProjectMembership } from "@/lib/api/client";

const pending = (job: BackgroundJob) => ["queued", "running", "retrying"].includes(job.status);
const labels = { queued: "Queued", running: "Running", retrying: "Retrying", completed: "Completed", failed: "Failed" };

function failureMessage(job: BackgroundJob): string {
  if (job.error_code === "dispatch_failed") return "This work could not be queued. Try again.";
  if (job.error_code === "dependency_unavailable") return "This work is awaiting a service connection. Try again after it is available.";
  if (job.error_code === "delivery_exhausted") return "Delivery stopped before this work completed. You can retry it.";
  return "This work failed. You can retry it.";
}

export function JobStatusPanel({ projectId }: { projectId: string }) {
  const [jobs, setJobs] = useState<BackgroundJob[]>([]);
  const [membership, setMembership] = useState<ProjectMembership | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const member = await getCurrentProjectMembership(projectId);
      const rows = await getJobs(projectId);
      const refreshed = await Promise.all(rows.map((job) => pending(job) && job.dispatched ? getJob(projectId, job.id) : job));
      setMembership(member);
      setJobs(refreshed);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Background work could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  const hasPendingWork = jobs.some(pending);
  useEffect(() => {
    if (!hasPendingWork) return;
    const timer = window.setInterval(() => { void load(); }, 5000);
    return () => window.clearInterval(timer);
  }, [hasPendingWork, load]);

  async function retry(job: BackgroundJob) {
    setRetrying(job.id);
    setError(null);
    try {
      const next = await retryJob(projectId, job);
      setJobs((current) => current.map((row) => row.id === next.id ? next : row));
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "This work could not be retried.");
    } finally {
      setRetrying(null);
    }
  }

  return <Panel className="job-status-panel">
    <div className="job-status-panel__header">
      <div><span className="eyebrow">WORK STATUS</span><h2>Background work</h2></div>
      <button type="button" className="button button--secondary" disabled={loading || retrying !== null} onClick={() => void load()}>Refresh status</button>
    </div>
    <div aria-live="polite">
      {error && <p role="alert" className="job-status-panel__error">{error}</p>}
      {loading ? <p>Loading background work…</p> : jobs.length === 0 && !error ? <p>No refresh or analysis jobs yet.</p> : null}
      <ul className="job-status-panel__list">{jobs.map((job) => <li key={job.id}>
        <div className="job-status-panel__header">
          <div><strong>{job.request.kind === "refresh" ? "Folder refresh" : "Evidence analysis"}</strong><p>{job.request.target_id}</p></div>
          <StatusPill tone={job.status === "failed" ? "danger" : job.status === "completed" ? "success" : "neutral"}>{labels[job.status]}</StatusPill>
        </div>
        {job.status === "failed" && <p>{failureMessage(job)}</p>}
        {job.status === "failed" && membership && membership.role !== "viewer" && (job.request.kind !== "refresh" || membership.role === "admin" || membership.refreshFolderId === job.request.target_id) &&
          <button type="button" className="button button--secondary" disabled={retrying !== null} onClick={() => void retry(job)}>{retrying === job.id ? "Retrying…" : "Retry work"}</button>}
      </li>)}</ul>
    </div>
  </Panel>;
}
