"use client";

import { useEffect, useState } from "react";
import { GoogleAuthProvider, User, onAuthStateChanged, signInWithPopup } from "firebase/auth";

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

  return <>{children}</>;
}
