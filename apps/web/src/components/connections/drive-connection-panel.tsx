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

export function DriveConnectionPanel({ projectId }: { projectId: string }) {
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
      const projectId = configuredProjectId();
      const result = await refreshDriveFolder(projectId, selected);
      setRefreshResult(result);
      setConnection(await getConnection(projectId));
      setSources(await listSources(projectId));
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Folder refresh failed.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <section className="panel mb-6 p-6 text-sm text-slate-600">
        Loading project access…
      </section>
    );
  }

  if (error && !membership) {
    return (
      <section className="panel mb-6 border-red-200 bg-red-50 p-6 text-sm text-red-700">
        {error}
      </section>
    );
  }

  if (membership?.role !== "admin") {
    return (
      <section className="panel mb-6 p-6 text-sm text-slate-600">
        Drive connection management is available to project administrators.
      </section>
    );
  }

  const isConnected = connection?.status === "active";
  const needsReconnect = connection?.status === "needs_reconnect";
  const connectLabel = isConnected || needsReconnect ? "Reconnect Drive" : "Connect Drive";

  return (
    <section className="panel mb-6 space-y-4 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">
            Drive connection
          </p>
          <h2 className="mt-2 text-lg font-semibold">Project evidence access</h2>
          <p className="mt-1 text-sm text-slate-600">
            Connect the Google account whose Drive folder the worker will read.
          </p>
        </div>
        <span
          className={`status-pill ${
            isConnected ? "status-pill--success" : "status-pill--warning"
          }`}
        >
          {connection?.status ?? "disconnected"}
        </span>
      </div>

      {connection?.authorization_pending && (
        <p className="rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-700">
          Waiting for Google authorization to finish.
        </p>
      )}

      {needsReconnect && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Google access needs to be granted again before the worker can refresh sources.
        </p>
      )}

      {callbackFailure === "storage_unavailable" && (
        <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Google authorization completed, but the server could not store the Drive grant. Check
          local Application Default Credentials and Secret Manager IAM access, then try again.
        </p>
      )}

      {callbackFailure === "authorization_failed" && (
        <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Google could not complete Drive authorization. Confirm the OAuth client and redirect URI,
          then try again.
        </p>
      )}

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          className="button button--primary"
          disabled={actionLoading}
          onClick={() => void beginAuthorization(isConnected || needsReconnect)}
        >
          {actionLoading ? "Opening Google…" : connectLabel}
        </button>
        {isConnected && (
          <button
            className="button button--secondary"
            disabled={actionLoading}
            onClick={() => void disconnect()}
          >
            Disconnect Drive
          </button>
        )}
      </div>

      {isConnected && (
        <div className="space-y-3 border-t border-slate-800 pt-4">
          <label htmlFor="drive-folder-id" className="block text-sm font-medium text-slate-200">
            Google Drive folder ID
          </label>
          <p className="text-xs text-slate-400">Copy the ID after /folders/ in the folder URL. Refresh reads this folder and one level of subfolders.</p>
          <div className="flex flex-wrap gap-3">
            <input
              id="drive-folder-id"
              value={folderId}
              onChange={(event) => setFolderId(event.target.value)}
              placeholder="Folder ID"
              className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
              disabled={actionLoading}
            />
            <button
              className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              disabled={actionLoading}
              onClick={() => void refreshFolder()}
            >
              {actionLoading ? "Refreshing…" : "Refresh folder"}
            </button>
          </div>
          {refreshResult && (
            <p role="status" className="text-sm text-emerald-300">
              Scanned {refreshResult.scanned} files: {refreshResult.created} new, {refreshResult.updated} updated, {refreshResult.unchanged} unchanged.
              {refreshResult.unsupported.length > 0 && ` Unsupported: ${refreshResult.unsupported.join(", ")}.`}
            </p>
          )}
          {sources.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Connected sources</h3>
              <ul className="mt-2 space-y-1 text-sm">
                {sources.map((source) => (
                  <li key={source.id}>
                    <a className="text-indigo-300 hover:underline" href={source.native_url} target="_blank" rel="noopener noreferrer">
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
