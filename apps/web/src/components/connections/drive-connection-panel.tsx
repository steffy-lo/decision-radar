"use client";

import { useCallback, useEffect, useState } from "react";

import {
  beginDriveAuthorization,
  disconnectDrive,
  getConnection,
  getCurrentProjectMembership,
  listSources,
  reconnectDrive,
  refreshDriveFolder,
} from "@/lib/api/client";
import type { Connection, FolderRefreshResult, ProjectMembership, SourceSummary } from "@/lib/api/client";

export function DriveConnectionPanel({ projectId, onSourcesChanged }: { projectId: string; onSourcesChanged?: () => void }) {
  const [membership, setMembership] = useState<ProjectMembership | null>(null);
  const [connection, setConnection] = useState<Connection | null>(null);
  const [folderId, setFolderId] = useState("");
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [refreshResult, setRefreshResult] = useState<FolderRefreshResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const callbackFailure =
    typeof window === "undefined"
      ? null
      : new URLSearchParams(window.location.search).get("reason");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const nextMembership = await getCurrentProjectMembership(projectId);
      setMembership(nextMembership);
      setError(null);

      if (nextMembership.role === "admin") {
        const nextConnection = await getConnection(projectId);
        setConnection(nextConnection);
        setFolderId(nextConnection.selected_folder_id ?? "");
        setSources(nextConnection.selected_folder_id ? await listSources(projectId) : []);
      } else {
        setConnection(null);
        setSources([]);
      }
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load Drive connection status.",
      );
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    // Defer the request until after the effect commits to avoid a synchronous render cascade.
    void Promise.resolve().then(load);
  }, [load]);

  const beginAuthorization = async (reconnect = false) => {
    setActionLoading(true);
    setError(null);
    try {
      const result = reconnect
        ? await reconnectDrive(projectId)
        : await beginDriveAuthorization(projectId);
      window.location.assign(result.authorization_url);
    } catch (actionError) {
      setError(
        actionError instanceof Error
          ? actionError.message
          : "Unable to start Drive authorization.",
      );
      setActionLoading(false);
    }
  };

  const disconnect = async () => {
    if (
      !window.confirm(
        "Disconnect the project's Drive account? The worker will no longer be able to refresh its sources.",
      )
    ) {
      return;
    }

    setActionLoading(true);
    setError(null);
    try {
      await disconnectDrive(projectId);
      await load();
    } catch (actionError) {
      setError(
        actionError instanceof Error
          ? actionError.message
          : "Unable to disconnect Drive.",
      );
    } finally {
      setActionLoading(false);
    }
  };

  const refreshFolder = async () => {
    const selected = folderId.trim();
    if (!selected) {
      setError("Enter the folder ID from its Google Drive URL.");
      return;
    }
    setActionLoading(true);
    setError(null);
    setRefreshResult(null);
    try {
      const result = await refreshDriveFolder(projectId, selected);
      setRefreshResult(result);
      setConnection(await getConnection(projectId));
      setSources(await listSources(projectId));
      onSourcesChanged?.();
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Folder refresh failed.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <section className="workspace-card connection-card" aria-busy="true">Loading Drive connection…</section>;
  }

  if (error && !membership) {
    return <section className="workspace-card connection-card"><p className="notice notice--error" role="alert">{error}</p></section>;
  }

  if (membership?.role !== "admin") {
    return <section className="workspace-card connection-card"><h2>Drive connection</h2><p className="supporting-copy">Project administrators manage the Drive connection.</p></section>;
  }

  const isConnected = connection?.status === "active";
  const needsReconnect = connection?.status === "needs_reconnect";
  const connectLabel = isConnected || needsReconnect ? "Reconnect Drive" : "Connect Drive";

  return (
    <section className="workspace-card connection-card">
      <div className="flow-card-heading">
        <span className="flow-step">1</span>
        <div className="flow-card-heading__copy">
          <span className="overline">CONNECTION</span>
          <h2>Connect your evidence</h2>
          <p>Choose the Google account and folder that hold the project updates.</p>
        </div>
        <span className={`status-pill status-pill--${isConnected ? "success" : "warning"}`}>{connection?.status?.replaceAll("_", " ") ?? "disconnected"}</span>
      </div>

      {connection?.authorization_pending && (
        <p className="notice notice--info">Waiting for Google authorization to finish.</p>
      )}

      {needsReconnect && (
        <p className="notice notice--warning">Reconnect Google Drive before refreshing the folder.</p>
      )}

      {callbackFailure === "storage_unavailable" && (
        <p className="notice notice--error">
          Google authorization completed, but the server could not store the Drive grant. Check
          local Application Default Credentials and Secret Manager IAM access, then try again.
        </p>
      )}

      {callbackFailure === "authorization_failed" && (
        <p className="notice notice--error">
          Google could not complete Drive authorization. Confirm the OAuth client and redirect URI,
          then try again.
        </p>
      )}

      {error && (
        <p role="alert" className="notice notice--error">{error}</p>
      )}

      <div className="flow-actions">
        <button
          className="button button--secondary"
          disabled={actionLoading}
          onClick={() => void beginAuthorization(isConnected || needsReconnect)}
        >
          {actionLoading ? "Opening Google…" : connectLabel}
        </button>
        {isConnected && (
          <button
            className="button button--quiet"
            disabled={actionLoading}
            onClick={() => void disconnect()}
          >
            Disconnect Drive
          </button>
        )}
      </div>

      {isConnected && (
        <div className="connection-folder">
          <label htmlFor="drive-folder-id" className="field-label">Google Drive folder ID</label>
          <p className="field-help">Copy the ID after <code>/folders/</code> in the Drive URL. We read this folder and one level of subfolders.</p>
          <div className="field-action-row">
            <input
              id="drive-folder-id"
              value={folderId}
              onChange={(event) => setFolderId(event.target.value)}
              placeholder="Folder ID"
              className="form-control"
              disabled={actionLoading}
            />
            <button
              className="button button--primary"
              disabled={actionLoading}
              onClick={() => void refreshFolder()}
            >
              {actionLoading ? "Refreshing…" : "Refresh folder"}
            </button>
          </div>
          {refreshResult && (
            <p role="status" className="notice notice--success">
              Scanned {refreshResult.scanned} files: {refreshResult.created} new, {refreshResult.updated} updated, {refreshResult.unchanged} unchanged.
              {refreshResult.unsupported.length > 0 && ` Unsupported: ${refreshResult.unsupported.join(", ")}.`}
            </p>
          )}
          {sources.length > 0 && (
            <div className="connected-summary">
              <h3>{sources.length} connected {sources.length === 1 ? "source" : "sources"}</h3>
              <ul>
                {sources.map((source) => (
                  <li key={source.id}>
                    <a href={source.native_url} target="_blank" rel="noopener noreferrer">
                      {source.name}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
