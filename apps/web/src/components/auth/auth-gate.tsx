"use client";

import { useEffect, useState } from "react";
import { User, onAuthStateChanged, signOut } from "firebase/auth";
import Link from "next/link";
import { googleSignInError, signInToWorkspace } from "@/lib/auth/google-sign-in";
import { DemoEntry } from "@/components/auth/demo-entry";
import { clearDemoSession, demoSessionExpiry } from "@/lib/auth/demo-session";
import { configureDemoWorkspace, getDemoFirebaseAuth, getFirebaseAuth } from "@/lib/auth/firebase";

export function AuthGate({ children, demoProjectId = null, demoEmail = "demo@decision-radar.example" }: { children: React.ReactNode; demoProjectId?: string | null; demoEmail?: string }) {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [signingIn, setSigningIn] = useState(false);
  useEffect(() => {
    if (demoProjectId) configureDemoWorkspace(demoProjectId);
    const auth = demoProjectId ? getDemoFirebaseAuth() : getFirebaseAuth();
    return onAuthStateChanged(auth, (next) => setUser(demoProjectId && next && demoSessionExpiry(next.uid) <= Date.now() ? null : next));
  }, [demoProjectId]);
  useEffect(() => {
    if (!demoProjectId || !user) return;
    const timer = window.setTimeout(() => {
      clearDemoSession(); setUser(null);
      void signOut(getDemoFirebaseAuth()).catch(() => {});
    }, Math.max(0, demoSessionExpiry(user.uid) - Date.now()));
    return () => window.clearTimeout(timer);
  }, [demoProjectId, user]);

  if (user === undefined) return <main className="auth-page">Checking your session…</main>;
  if (!user && demoProjectId) return <DemoEntry projectId={demoProjectId} email={demoEmail} onReady={setUser} />;
  if (!user) return <main className="auth-page"><section className="auth-page__card">
    <span className="section-kicker">DECISION RADAR</span><h1>Sign in to your workspace</h1>
    <p>Use your workspace account to access project decisions and evidence.</p>
    <p><Link className="text-link" href="/login">Find your workspaces or switch Google account →</Link></p>
    <button className="button button--primary" disabled={signingIn} onClick={async () => {
      setSigningIn(true); setError(null);
      try { await signInToWorkspace(); }
      catch (value) { setError(googleSignInError(value)); }
      finally { setSigningIn(false); }
    }}>Continue with Google</button>
    {error && <p className="notice notice--error" role="alert">{error}</p>}
  </section></main>;
  return <>
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <div className="auth-session"><span className="auth-session__email">{demoProjectId ? demoEmail : user.email ?? "Signed-in user"}</span>
      {!demoProjectId && <Link className="auth-session__action" href="/login">Workspaces</Link>}
      <button className="auth-session__action" onClick={async () => {
        try {
          if (demoProjectId) clearDemoSession();
          await signOut(demoProjectId ? getDemoFirebaseAuth() : getFirebaseAuth()); setError(null);
        } catch (value) { setError(value instanceof Error ? value.message : "Sign-out failed."); }
      }}>Sign out</button>
    </div>
    {error && <p className="auth-session__error notice notice--error" role="alert">{error}</p>}
    {children}
  </>;
}
