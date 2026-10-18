"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { onAuthStateChanged, signOut, type User } from "firebase/auth";
import { getPersonalFirebaseAuth } from "@/lib/auth/firebase";
import { googleSignInError, signInToWorkspace } from "@/lib/auth/google-sign-in";
import { listMyWorkspaces, type WorkspaceSummary } from "@/lib/api/client";

export function WorkspaceLogin() {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loaded, setLoaded] = useState<{ uid: string; rows: WorkspaceSummary[] | null; error: boolean } | null>(null);

  useEffect(() => onAuthStateChanged(getPersonalFirebaseAuth(), (next) => {
    setUser(next?.providerData.some((provider) => provider.providerId === "google.com") ? next : null);
  }), []);

  useEffect(() => {
    let cancelled = false;
    if (!user) return;
    void Promise.resolve().then(async () => {
      if (cancelled) return;
      setLoaded({ uid: user.uid, rows: null, error: false });
      try {
        const rows = await listMyWorkspaces();
        if (!cancelled) setLoaded({ uid: user.uid, rows, error: false });
      } catch { if (!cancelled) setLoaded({ uid: user.uid, rows: null, error: true }); }
    });
    return () => { cancelled = true; };
  }, [user, attempt]);

  async function signIn() {
    setBusy(true); setError(null);
    try { await signInToWorkspace(); }
    catch (value) { setError(googleSignInError(value)); }
    finally { setBusy(false); }
  }

  const current = user && loaded?.uid === user.uid ? loaded : null;
  return <main className="auth-page"><section className="auth-page__card workspace-login">
    <Link className="text-link" href="/">← Home</Link>
    <span className="section-kicker">DECISION RADAR</span>
    <h1>{user ? "Choose your workspace" : "Sign in to your workspace"}</h1>
    {user === undefined ? <p role="status">Checking your Google session…</p> : !user ? <>
      <p>Use the Google account that has been given access to your project. Gmail and Google Workspace accounts are supported.</p>
      <button className="button button--primary" disabled={busy} onClick={() => void signIn()}>{busy ? "Opening Google…" : "Continue with Google"}</button>
      <p className="field-help">Signing in opens existing workspace access. Ask the project owner for an invitation if you do not have access yet.</p>
    </> : <>
      <p>Signed in as <strong>{user.email}</strong>.</p>
      {!current || (!current.rows && !current.error) ? <p role="status">Finding your workspaces…</p> : current.error ? <div role="alert"><p>Your workspaces could not be loaded.</p><button className="button button--secondary" onClick={() => setAttempt((value) => value + 1)}>Try loading again</button></div> : current.rows?.length ? <ul className="workspace-login__list">{current.rows.map((workspace) => <li key={workspace.id}>
        <Link className="workspace-login__project" href={`/projects/${encodeURIComponent(workspace.id)}/connections`}><strong>{workspace.name}</strong><span>{workspace.role === "admin" ? "Administrator" : workspace.role === "editor" ? "Can edit" : "Can view"} · Open workspace →</span></Link>
      </li>)}</ul> : <p role="status" className="notice notice--info">No workspace access yet. Ask the project owner to invite {user.email}, or choose a different Google account.</p>}
      <div className="extraction-action"><button className="button button--secondary" disabled={busy} onClick={() => void signIn()}>{busy ? "Opening Google…" : "Use another Google account"}</button>
        <button className="button button--secondary" disabled={busy} onClick={async () => {
          setBusy(true); setError(null);
          try { await signOut(getPersonalFirebaseAuth()); setLoaded(null); }
          catch { setError("Sign-out could not be completed. Please try again."); }
          finally { setBusy(false); }
        }}>Sign out</button></div>
    </>}
    {error && <p className="notice notice--error" role="alert">{error}</p>}
    <p><Link className="text-link" href="/demo">Try the sample workspace without signing in →</Link></p>
  </section></main>;
}
