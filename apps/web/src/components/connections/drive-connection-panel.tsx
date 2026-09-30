"use client";

import { useCallback, useEffect, useState } from "react";

import {
  beginDriveAuthorization,
  disconnectDrive,
  getConnection,
  getCurrentProjectMembership,
  reconnectDrive,
} from "@/lib/api/client";
import type { Connection, ProjectMembership } from "@/lib/api/client";

export function DriveConnectionPanel({ projectId }: { projectId: string }) {
  const [membership, setMembership] = useState<ProjectMembership | null>(null);
  const [connection, setConnection] = useState<Connection | null>(null);
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
        setConnection(await getConnection(projectId));
      } else {
        setConnection(null);
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
    </section>
  );
}
