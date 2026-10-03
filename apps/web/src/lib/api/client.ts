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
  selected_folder_id: string | null;
  error_code: string | null;
  authorization_pending: boolean;
  updated_at: string | null;
}

export interface SourceSummary {
  id: string;
  name: string;
  mime_type: string;
  native_url: string;
  status: string;
  failure_reason: string | null;
}

export interface FolderRefreshResult {
  scanned: number;
  created: number;
  updated: number;
  unchanged: number;
  removed: number;
  unsupported: string[];
}

export async function listSources(projectId: string): Promise<SourceSummary[]> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/sources`);
  if (!response.ok) throw new Error(`Source list failed with status ${response.status}.`);
  return response.json();
}

export async function refreshDriveFolder(projectId: string, folderId: string): Promise<FolderRefreshResult> {
  const response = await fetchPrivateApi(
    `/api/v1/projects/${encodeURIComponent(projectId)}/sources/refresh`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ folder_id: folderId }) },
  );
  if (!response.ok) {
    const payload: { detail?: string } = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Folder refresh failed with status ${response.status}.`);
  }
  return response.json();
}

export interface AuthorizeConnectionResponse {
  authorization_url: string;
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
