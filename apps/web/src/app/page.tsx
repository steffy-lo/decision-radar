"use client";

import { useEffect, useState } from "react";
import { AuthGate } from "@/components/auth/auth-gate";
import { DriveConnectionPanel } from "@/components/connections/drive-connection-panel";
import { checkBackendHealth } from "@/lib/api/client";
import type { HealthResponse } from "@/lib/api/client";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkBackendHealth()
      .then((data) => {
        setHealth(data);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || "Failed to reach backend via Next.js proxy");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <AuthGate>
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6">
      <main className="max-w-2xl w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl space-y-6">
        <div className="flex items-center space-x-3 border-b border-slate-800 pb-4">
          <div className="h-4 w-4 rounded-full bg-indigo-500 animate-pulse" />
          <h1 className="text-2xl font-bold tracking-tight text-white">Decision Radar Platform</h1>
        </div>

        <p className="text-slate-400 text-sm leading-relaxed">
          Organisational-memory and decision-intelligence platform foundation. Scaffolding for Next.js App Router, FastAPI backend, and background worker infrastructure.
        </p>

        <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">FastAPI Proxy Health Route</span>
            <span className="text-xs text-slate-400">Target: <code className="text-indigo-400">/api/v1/health</code></span>
          </div>

          {loading ? (
            <div className="flex items-center space-x-2 text-slate-400 text-sm py-2">
              <svg className="animate-spin h-4 w-4 text-indigo-400" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span>Connecting to FastAPI backend via Next.js proxy...</span>
            </div>
          ) : error ? (
            <div className="bg-red-950/40 border border-red-800/60 rounded-lg p-3 text-red-300 text-xs">
              <p className="font-semibold">Proxy Connection Error</p>
              <p className="mt-1 font-mono text-[11px] opacity-80">{error}</p>
            </div>
          ) : (
            <div className="bg-emerald-950/30 border border-emerald-800/50 rounded-lg p-4 space-y-2 text-xs font-mono text-emerald-200">
              <div className="flex justify-between">
                <span className="text-slate-400">Status:</span>
                <span className="font-bold text-emerald-400">{health?.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Service:</span>
                <span>{health?.service}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Environment:</span>
                <span>{health?.environment}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Timestamp:</span>
                <span>{health?.timestamp}</span>
              </div>
            </div>
          )}
        </div>

        <DriveConnectionPanel />

        <div className="grid grid-cols-3 gap-3 pt-2 text-center text-xs">
          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
            <div className="font-semibold text-slate-200">apps/web</div>
            <div className="text-[11px] text-slate-500 mt-1">Next.js App Router</div>
          </div>
          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
            <div className="font-semibold text-slate-200">services/radar</div>
            <div className="text-[11px] text-slate-500 mt-1">FastAPI Backend</div>
          </div>
          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
            <div className="font-semibold text-slate-200">infra</div>
            <div className="text-[11px] text-slate-500 mt-1">Firebase Emulators</div>
          </div>
        </div>
      </main>
    </div>
    </AuthGate>
  );
}
