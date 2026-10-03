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

export interface Connection {
  id: "google-drive";
  project_id: string;
  status: "pending" | "active" | "needs_reconnect" | "disconnected" | "error";
  account_email: string | null;
  error_code: string | null;
  authorization_pending: boolean;
  updated_at: string | null;
}

export interface AuthorizeConnectionResponse {
  authorization_url: string;
}

export interface BackgroundJob {
  id: string;
  project_id: string;
  request: { kind: "refresh" | "analysis"; target_id: string; source_version: string };
  generation: number;
  status: "queued" | "running" | "retrying" | "completed" | "failed";
  attempts: number;
  dispatched: boolean;
  error_code: "dispatch_failed" | "handler_failed" | "dependency_unavailable" | "delivery_exhausted" | null;
  updated_at: string;
}

async function jobResponse(response: Response): Promise<BackgroundJob> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : "Job request could not be completed.");
  }
  return response.json();
}

export async function getJobs(projectId: string): Promise<BackgroundJob[]> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/jobs`);
  if (!response.ok) throw new Error("Background work could not be loaded.");
  return response.json();
}

export async function getJob(projectId: string, jobId: string): Promise<BackgroundJob> {
  return jobResponse(await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/jobs/${encodeURIComponent(jobId)}`));
}

export async function retryJob(projectId: string, job: BackgroundJob): Promise<BackgroundJob> {
  return jobResponse(await fetchPrivateApi(
    `/api/v1/projects/${encodeURIComponent(projectId)}/jobs/${encodeURIComponent(job.id)}/retry`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ generation: job.generation }) },
  ));
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

export async function getConnection(projectId: string): Promise<Connection> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/connections/google-drive`);
  if (!response.ok) throw new Error(`Connection lookup failed with status ${response.status}.`);
  return response.json();
}

export async function beginDriveAuthorization(projectId: string): Promise<AuthorizeConnectionResponse> {
  const response = await fetchPrivateApi(
    `/api/v1/projects/${encodeURIComponent(projectId)}/connections/google-drive/authorize`,
    { method: "POST" },
  );
  if (!response.ok) throw new Error(`Drive authorization could not start with status ${response.status}.`);
  return response.json();
}

export async function reconnectDrive(projectId: string): Promise<AuthorizeConnectionResponse> {
  const response = await fetchPrivateApi(
    `/api/v1/projects/${encodeURIComponent(projectId)}/connections/google-drive/reconnect`,
    { method: "POST" },
  );
  if (!response.ok) throw new Error(`Drive reconnect could not start with status ${response.status}.`);
  return response.json();
}

export async function disconnectDrive(projectId: string): Promise<void> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/connections/google-drive`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error(`Drive disconnect failed with status ${response.status}.`);
}

export async function checkBackendHealth(): Promise<HealthResponse> {
  const res = await fetch("/api/v1/health", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}: ${res.statusText}`);
  }
  return res.json();
}
