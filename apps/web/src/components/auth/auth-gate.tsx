"use client";

import { useEffect, useState } from "react";
import { GoogleAuthProvider, User, onAuthStateChanged, signInWithPopup, signOut } from "firebase/auth";

import { getFirebaseAuth } from "@/lib/auth/firebase";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => onAuthStateChanged(getFirebaseAuth(), setUser), []);

  if (user === undefined) {
    return <main className="auth-page">Checking your session…</main>;
  }

  if (!user) {
    return (
      <main className="auth-page">
        <section className="auth-page__card">
          <span className="overline">DECISION RADAR</span>
          <h1>Sign in to your workspace</h1>
          <p>Use your workspace account to access project decisions and evidence.</p>
          <button
            className="button button--primary"
            onClick={async () => {
              try {
                await signInWithPopup(getFirebaseAuth(), new GoogleAuthProvider());
                setError(null);
              } catch (signInError) {
                setError(signInError instanceof Error ? signInError.message : "Sign-in failed.");
              }
            }}
          >
            Continue with Google
          </button>
          {error && <p className="notice notice--error" role="alert">{error}</p>}
        </section>
      </main>
    );
  }

  return (
    <>
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
