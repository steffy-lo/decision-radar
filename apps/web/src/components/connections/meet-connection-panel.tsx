"use client";

import { useCallback, useEffect, useState } from "react";
import {
  beginMeetAuthorization, getCurrentProjectMembership, getMeetConnection,
  listMeetSpaces, monitorMeetSpace, reconcileMeetSpace, stopMeetSpace,
} from "@/lib/api/client";
import type { Connection, MeetSpace } from "@/lib/api/client";

function message(error: unknown): string {
  return error instanceof Error ? error.message : "The Meet request failed.";
}

export function MeetConnectionPanel({ projectId }: { projectId: string }) {
  const [isAdmin, setIsAdmin] = useState(false);
  const [connection, setConnection] = useState<Connection | null>(null);
  const [spaces, setSpaces] = useState<MeetSpace[]>([]);
  const [spaceName, setSpaceName] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [member, nextConnection, nextSpaces] = await Promise.all([
        getCurrentProjectMembership(projectId), getMeetConnection(projectId), listMeetSpaces(projectId),
      ]);
      setIsAdmin(member.role === "admin");
      setConnection(nextConnection);
      setSpaces(nextSpaces);
      setError(null);
    } catch (value) {
      setError(message(value));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const authorization = await beginMeetAuthorization(projectId);
      window.location.assign(authorization.authorization_url);
    } catch (value) {
      setError(message(value));
      setBusy(false);
    }
  }

  async function addSpace() {
    setBusy(true);
    setError(null);
    try {
      const next = await monitorMeetSpace(projectId, spaceName.trim());
      setSpaces((current) => [...current.filter((row) => row.spaceName !== next.spaceName), next]);
      setSpaceName("");
    } catch (value) {
      setError(message(value));
    } finally {
      setBusy(false);
    }
  }

  async function checkSpace(space: MeetSpace) {
    setBusy(true);
    setError(null);
    try {
      const next = await reconcileMeetSpace(projectId, space.spaceName.split("/")[1]);
      setSpaces((current) => current.map((row) => row.spaceName === next.spaceName ? next : row));
    } catch (value) {
      setError(message(value));
    } finally {
      setBusy(false);
    }
  }

  async function stopSpace(space: MeetSpace) {
    setBusy(true);
    setError(null);
    try {
      const next = await stopMeetSpace(projectId, space.spaceName.split("/")[1]);
      setSpaces((current) => current.map((row) => row.spaceName === next.spaceName ? next : row));
    } catch (value) {
      setError(message(value));
    } finally {
      setBusy(false);
    }
  }

  return <section className="panel mb-6 space-y-4 p-6" aria-label="Google Meet transcript monitoring">
    <div>
      <p className="eyebrow">Meet connection</p>
      <h2 className="mt-2 text-lg font-semibold">Transcript monitoring</h2>
      <p className="mt-1 text-sm text-slate-600">Connect an account with access to the meeting, then paste its Meet link or code. Generated transcripts will appear in Sources.</p>
    </div>
    {loading && <p role="status">Loading Meet connection…</p>}
    {error && <p role="alert" className="notice notice--error">{error}</p>}
    {!loading && <p role="status">Meet connection: {connection?.status ?? "unavailable"}</p>}
    {!loading && isAdmin && <button className="button button--secondary" disabled={busy} onClick={() => void connect()}>{connection?.status === "active" ? "Reconnect Meet" : "Connect Meet"}</button>}
    {connection?.status === "active" && isAdmin && <div className="flex flex-wrap items-end gap-3">
      <label className="form-field">Meet link or code
        <input className="form-control" value={spaceName} onChange={(event) => setSpaceName(event.target.value)} placeholder="https://meet.google.com/abc-defg-hij" />
      </label>
      <button className="button button--primary" disabled={busy || !spaceName.trim() || spaces.filter((space) => ["active", "pending", "stopping"].includes(space.status)).length >= 5} onClick={() => void addSpace()}>Monitor space</button>
    </div>}
    {spaces.length > 0 && <ul className="space-y-2">{spaces.map((space) => <li className="rounded-lg border border-slate-200 p-3" key={space.spaceName}>
      <strong>{space.spaceName}</strong> · {space.status}
      {space.expiresAt && <span className="ml-2 text-sm text-slate-600">Expires {new Date(space.expiresAt).toLocaleString()}</span>}
      {["pending", "stopping"].includes(space.status) && isAdmin && <button className="button button--secondary ml-3" disabled={busy} onClick={() => void checkSpace(space)}>Check status</button>}
      {space.status === "active" && isAdmin && <button className="button button--secondary ml-3" disabled={busy} onClick={() => void stopSpace(space)}>Stop monitoring</button>}
      {space.errorCode && <p role="alert" className="notice notice--error">{space.errorCode}</p>}
    </li>)}</ul>}
  </section>;
}
