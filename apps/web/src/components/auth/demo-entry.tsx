"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { User } from "firebase/auth";
import { startDemoSession } from "@/lib/auth/demo-session";

export function DemoEntry({ projectId, email, onReady }: { projectId: string; email: string; onReady?: (user: User) => void }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return <main className="auth-page"><section className="auth-page__card">
    <span className="section-kicker">DECISION RADAR</span><h1>Try the connected demo</h1>
    <p>Explore real Drive connections and Gemini assessments using sample project documents. No password or email verification is needed.</p>
    <form className="auth-page__form" onSubmit={async (event) => {
      event.preventDefault(); setBusy(true); setError(null);
      try {
        const user = await startDemoSession(projectId);
        if (onReady) onReady(user);
        else router.replace(`/projects/${encodeURIComponent(projectId)}/connections`);
      } catch (value) {
        setError(value instanceof Error && !value.message.startsWith("Firebase:") ? value.message : "Demo sign-in is temporarily unavailable. Please try again.");
      } finally { setBusy(false); }
    }}>
      <label className="form-field">Demo email<input className="form-control" type="email" readOnly value={email} autoComplete="off" /><span className="field-help">The sample workspace label. Each visitor gets a separate session.</span></label>
      <button type="submit" className="button button--primary" disabled={busy}>{busy ? "Opening demo…" : "Try demo"}</button>
    </form>
    {error && <p role="alert" className="notice notice--error">{error}</p>}
    <p><Link className="text-link" href="/login">Have a workspace? Sign in with Google →</Link></p>
    <p className="field-help">Sessions last one hour. Sample decisions and reviews are shared and changes are retained.</p>
  </section></main>;
}
