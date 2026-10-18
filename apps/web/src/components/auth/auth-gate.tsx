"use client";

import { useEffect, useState } from "react";
import { GoogleAuthProvider, User, onAuthStateChanged, signInWithEmailAndPassword, signInWithPopup, signOut } from "firebase/auth";

import { getFirebaseAuth } from "@/lib/auth/firebase";

export function AuthGate({ children, judgeWorkspace = false }: { children: React.ReactNode; judgeWorkspace?: boolean }) {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [signingIn, setSigningIn] = useState(false);

  useEffect(() => onAuthStateChanged(getFirebaseAuth(), setUser), []);

  if (user === undefined) {
    return <main className="auth-page">Checking your session…</main>;
  }

  if (!user) {
    return (
      <main className="auth-page">
        <section className="auth-page__card">
          <span className="section-kicker">DECISION RADAR</span>
          <h1>{judgeWorkspace ? "Try the connected demo" : "Sign in to your workspace"}</h1>
          <p>{judgeWorkspace ? "Use the judge account supplied with the submission. This workspace reads real Google Docs containing sample project data and runs Gemini assessments." : "Use your workspace account to access project decisions and evidence."}</p>
          {judgeWorkspace && <form className="auth-page__form" onSubmit={async (event) => {
            event.preventDefault();
            setSigningIn(true);
            setError(null);
            try {
              await signInWithEmailAndPassword(getFirebaseAuth(), email.trim(), password);
              setPassword("");
            } catch {
              setError("Unable to sign in. Check the judge email and password, then try again.");
            } finally { setSigningIn(false); }
          }}>
            <label className="form-field">Judge email<input className="form-control" type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
            <label className="form-field">Password<input className="form-control" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            <button className="button button--primary" type="submit" disabled={signingIn}>{signingIn ? "Signing in…" : "Sign in as judge"}</button>
          </form>}
          <button
            className="button button--primary"
            disabled={signingIn}
            onClick={async () => {
              setSigningIn(true);
              setError(null);
              try {
                await signInWithPopup(getFirebaseAuth(), new GoogleAuthProvider());
                setError(null);
              } catch (signInError) {
                setError(signInError instanceof Error ? signInError.message : "Sign-in failed.");
              } finally { setSigningIn(false); }
            }}
          >
            {judgeWorkspace ? "Use an invited Google account" : "Continue with Google"}
          </button>
          {error && <p className="notice notice--error" role="alert">{error}</p>}
        </section>
      </main>
    );
  }

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <div className="auth-session">
        <span className="auth-session__email">{user.email ?? "Signed-in user"}</span>
        <button
          className="auth-session__action"
          onClick={async () => {
            try {
              await signOut(getFirebaseAuth());
              setError(null);
            } catch (signOutError) {
              setError(signOutError instanceof Error ? signOutError.message : "Sign-out failed.");
            }
          }}
        >
          Sign out
        </button>
      </div>
      {error && <p className="auth-session__error notice notice--error" role="alert">{error}</p>}
      {children}
    </>
  );
}
