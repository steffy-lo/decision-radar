"use client";

import { browserSessionPersistence, setPersistence, signInAnonymously, signOut } from "firebase/auth";
import { configureDemoWorkspace, getDemoFirebaseAuth } from "@/lib/auth/firebase";

const sessionKey = "decision-radar.demo-session";

export function demoSessionExpiry(uid: string): number {
  try {
    const value = JSON.parse(sessionStorage.getItem(sessionKey) ?? "null");
    return value?.uid === uid ? Date.parse(value.expiresAt) || 0 : 0;
  } catch { return 0; }
}

export function clearDemoSession(): void { sessionStorage.removeItem(sessionKey); }

export async function startDemoSession(projectId: string) {
  configureDemoWorkspace(projectId);
  const auth = getDemoFirebaseAuth();
  await setPersistence(auth, browserSessionPersistence);
  await auth.authStateReady();
  if (auth.currentUser) await signOut(auth);
  clearDemoSession();
  try {
    const { user } = await signInAnonymously(auth);
    const response = await fetch("/api/v1/demo/session", {
      method: "POST", cache: "no-store",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${await user.getIdToken()}` },
      body: "{}",
    });
    const result = await response.json().catch(() => null);
    if (!response.ok) throw new Error(typeof result?.detail === "string" ? result.detail : "The demo could not be opened. Please try again.");
    if (result?.projectId !== projectId || !Number.isFinite(Date.parse(result?.expiresAt))) throw new Error("The demo configuration changed. Reload this page and try again.");
    sessionStorage.setItem(sessionKey, JSON.stringify({ uid: user.uid, expiresAt: result.expiresAt }));
    return user;
  } catch (error) {
    await signOut(auth).catch(() => {});
    throw error;
  }
}
