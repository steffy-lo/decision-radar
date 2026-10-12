"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { DriveConnectionPanel } from "@/components/connections/drive-connection-panel";
import { PageHeading, Panel, StatusPill } from "@/components/ui";
import { getCurrentProjectMembership, listSources, setSourceMonitoring } from "@/lib/api/client";
import type { ProjectMembership, SourceSummary } from "@/lib/api/client";

function dateLabel(value: string | null): string {
  if (!value) return "Not available";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Not available" : parsed.toLocaleString();
}

export function ConnectionSetupWorkspace({ projectId }: { projectId: string }) {
  const [membership, setMembership] = useState<ProjectMembership | null>(null);
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [busySource, setBusySource] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [member, rows] = await Promise.all([getCurrentProjectMembership(projectId), listSources(projectId)]);
      setMembership(member);
      setSources(rows);
      setError(null);
    } catch (value) { setError(value instanceof Error ? value.message : "Source setup could not be loaded."); }
    finally { setLoading(false); }
  }, [projectId]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function setPaused(source: SourceSummary, paused: boolean) {
    setBusySource(source.id);
    setError(null);
    try {
      const updated = await setSourceMonitoring(projectId, source.id, paused);
      setSources((rows) => rows.map((row) => row.id === source.id ? updated : row));
    } catch (value) { setError(value instanceof Error ? value.message : "Source monitoring could not be changed."); }
    finally { setBusySource(null); }
  }

  return <>
    <PageHeading eyebrow="SOURCE SETUP" title="Connections" description="Choose the Drive folder to monitor and check each source before assessment." />
    <DriveConnectionPanel projectId={projectId} onSourcesChanged={() => void load()} />
    <Panel className="workspace-card workspace-card--spaced">
      <div className="flow-card-heading"><div className="flow-card-heading__copy"><span className="section-kicker">MONITORED SCOPE</span><h2>Folder inventory</h2><p>Refresh the connected folder to discover files. A source is assessed only after it is ready and monitoring is active.</p></div></div>
      {error && <p role="alert" className="notice notice--error">{error}</p>}
      {loading ? <p role="status">Loading source status…</p> : sources.length === 0 ? <p>No files are monitored yet. Connect Drive and refresh a folder above.</p> : <>
        <p role="status">{sources.length} {sources.length === 1 ? "source" : "sources"} in the selected folder · {sources.filter((row) => row.status === "ready" && !row.monitoring_paused).length} ready for monitoring.</p>
        <ul className="workspace-stack">{sources.map((source) => <li key={source.id}>
          <Panel className="workspace-card source-item">
            <div className="source-item__head"><div><h3>{source.name}</h3><p>Drive modified: {dateLabel(source.last_modified)} · Last refreshed: {dateLabel(source.updated_at)}</p></div><StatusPill tone={source.monitoring_paused || source.status !== "ready" ? "warning" : "success"}>{source.monitoring_paused ? "Paused" : source.status}</StatusPill></div>
            {source.failure_reason && <p role="status" className="notice notice--warning">{source.failure_reason}</p>}
            <div className="flex flex-wrap gap-3">
              <Link className="button button--secondary" href={`/projects/${encodeURIComponent(projectId)}/sources`}>{source.table_mapping || ["application/vnd.google-apps.spreadsheet", "text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"].includes(source.mime_type) ? "Configure table mapping" : "Inspect source"}</Link>
              {membership?.role === "admin" && <button type="button" className="button button--secondary" disabled={busySource !== null || (source.monitoring_paused && source.status !== "ready")} onClick={() => void setPaused(source, !source.monitoring_paused)}>{busySource === source.id ? "Saving…" : source.monitoring_paused ? "Resume monitoring" : "Pause monitoring"}</button>}
            </div>
          </Panel>
        </li>)}</ul>
        <p className="supporting-copy">Pausing a source removes its facts from the next assessment. Existing alerts remain in history until you run a new assessment.</p>
      </>}
    </Panel>
  </>;
}
