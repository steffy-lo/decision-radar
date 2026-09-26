import { getFirebaseAuth } from "@/lib/auth/firebase";

export interface HealthResponse {
  status: string;
  service: string;
  timestamp: string;
  environment: string;
}

export interface ProjectMembership {
  uid: string;
  role: "admin" | "editor" | "viewer";
  projectId: string;
}

export class AuthenticationRequiredError extends Error {
  constructor() {
    super("Please sign in before accessing workspace data.");
  }
}

export async function fetchPrivateApi(path: string, init: RequestInit = {}): Promise<Response> {
  if (!path.startsWith("/api/v1/")) {
    throw new Error("Private API paths must use the same-origin /api/v1 boundary.");
  }

  const auth = getFirebaseAuth();
  await auth.authStateReady();
  const user = auth.currentUser;
  if (!user) throw new AuthenticationRequiredError();

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${await user.getIdToken()}`);
  return fetch(path, { ...init, headers, cache: "no-store" });
}

export async function getCurrentProjectMembership(projectId: string): Promise<ProjectMembership> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/me`);
  if (!response.ok) {
    throw new Error(`Workspace membership check failed with status ${response.status}.`);
  }
  return response.json();
}

export async function checkBackendHealth(): Promise<HealthResponse> {
  const res = await fetch("/api/v1/health", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}: ${res.statusText}`);
  }
  return res.json();
}
