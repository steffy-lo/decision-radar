"use client";

import { useEffect, useState } from "react";
import { GoogleAuthProvider, User, onAuthStateChanged, signInWithPopup, signOut } from "firebase/auth";

import { getFirebaseAuth } from "@/lib/auth/firebase";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => onAuthStateChanged(getFirebaseAuth(), setUser), []);

  if (user === undefined) {
    return <main className="min-h-screen bg-slate-950 p-6 text-slate-300">Checking your session…</main>;
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100">
        <section className="w-full max-w-sm space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-8">
          <h1 className="text-xl font-semibold">Sign in to Decision Radar</h1>
          <p className="text-sm text-slate-400">Use your workspace account to access project data.</p>
          <button
            className="w-full rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold hover:bg-indigo-400"
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
          {error && <p className="text-sm text-red-300">{error}</p>}
        </section>
      </main>
    );
  }

  return (
    <>
      <div className="fixed right-4 top-4 z-10 flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/95 px-3 py-2 text-xs shadow-lg">
        <span className="max-w-48 truncate text-slate-400">{user.email ?? "Signed-in user"}</span>
        <button
          className="font-semibold text-slate-200 hover:text-white"
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
      {error && <p className="fixed right-4 top-16 z-10 max-w-sm rounded-lg bg-red-950 p-3 text-sm text-red-300">{error}</p>}
      {children}
    </>
  );
}
