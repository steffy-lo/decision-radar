"use client";

import { FirebaseApp, getApp, getApps, initializeApp } from "firebase/app";
import { Auth, connectAuthEmulator, getAuth } from "firebase/auth";

const config = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

const emulatorConnections = new Set<string>();
let demoProjectId: string | null = null;

export function configureDemoWorkspace(projectId: string): void {
  demoProjectId = projectId;
}

export function getFirebaseApp(): FirebaseApp {
  return getApps().some((app) => app.name === "[DEFAULT]") ? getApp() : initializeApp(config);
}

function configuredAuth(app: FirebaseApp): Auth {
  const auth = getAuth(app);
  const emulatorUrl = process.env.NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_URL;
  if (emulatorUrl && !emulatorConnections.has(app.name)) {
    connectAuthEmulator(auth, emulatorUrl, { disableWarnings: true });
    emulatorConnections.add(app.name);
  }
  return auth;
}

export function getDemoFirebaseAuth(): Auth {
  const name = "connected-demo";
  return configuredAuth(getApps().some((app) => app.name === name) ? getApp(name) : initializeApp(config, name));
}

export function getFirebaseAuth(): Auth {
  const path = typeof window === "undefined" ? "" : window.location.pathname;
  return demoProjectId && path.startsWith(`/projects/${encodeURIComponent(demoProjectId)}/`)
    ? getDemoFirebaseAuth() : configuredAuth(getFirebaseApp());
}
