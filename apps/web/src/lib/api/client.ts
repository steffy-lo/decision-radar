import { getFirebaseAuth } from "@/lib/auth/firebase";
import type { EvidenceRef } from "@/lib/domain/models";

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

export interface MonitoredAssumption {
  id: string;
  statement: string;
  predicate: string;
  entityId: string;
  decisionId: string;
  decisionStatement: string;
}

export interface ExtractionResult {
  sourceId: string;
  assumptionId: string;
  createdAt: string;
  publishedFactCount: number;
  decisions: { statement: string; quote: string; uncertainReason: string | null }[];
  facts: { entity: string; predicate: string; value: { type: string; value: string }; quote: string; state: string; uncertainReason: string | null }[];
}

export interface AssessmentResults {
  latestRun: { runId: string; findingCount: number; alertCount: number; coverage: { assumption_id: string; state: string; reason: string }[] } | null;
  findings: { id: string; assumptionId: string; classification: string; reasonCode: string; deltaDays: number | null; baselineEvidence: EvidenceRef; updateEvidence: EvidenceRef }[];
  alerts: { id: string; findingId: string; decisionId: string; severity: string; reviewState: string }[];
}

export type ReviewAction = "keep" | "revise" | "retire" | "dismiss" | "request_clarification";

export interface ReviewHistory {
  decision: LiveDecision;
  revisions: { id: string; revision: number; statement: string }[];
  reviews: { id: string; action: ReviewAction; rationale: string; actorId: string; beforeRevision: number | null; afterRevision: number | null; createdAt: string }[];
}

export async function getReviewHistory(projectId: string, alertId: string): Promise<ReviewHistory> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/alerts/${encodeURIComponent(alertId)}/reviews`);
  if (!response.ok) throw new Error(`Review history failed with status ${response.status}.`);
  return response.json();
}

export async function submitAlertReview(
  projectId: string, alertId: string, version: number,
  action: ReviewAction, rationale: string, revisedStatement?: string,
): Promise<void> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/alerts/${encodeURIComponent(alertId)}/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID(), "If-Match": `"${version}"` },
    body: JSON.stringify({ action, rationale, revisedStatement: action === "revise" ? revisedStatement : null }),
  });
  if (!response.ok) {
    const payload: { detail?: string } = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Review failed with status ${response.status}.`);
  }
}

export interface LiveDecision {
  id: string;
  statement: string;
  owner: string;
  rationale: string;
  status: "draft" | "active" | "retired";
  version: number;
  activeRevision: number;
}

export interface SourceDetail {
  id: string;
  name: string;
  nativeUrl: string;
  contentSnapshot: string;
  status: string;
}

export async function listLiveDecisions(projectId: string): Promise<LiveDecision[]> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/decisions`);
  if (!response.ok) throw new Error(`Decision list failed with status ${response.status}.`);
  return response.json();
}

export async function getSourceDetail(projectId: string, sourceId: string): Promise<SourceDetail> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(sourceId)}`);
  if (!response.ok) throw new Error(`Source lookup failed with status ${response.status}.`);
  return response.json();
}

function decisionErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) return fallback;
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return fallback;
  const fieldNames: Record<string, string> = {
    statement: "Decision statement", owner: "Owner", rationale: "Rationale",
    "assumptions.0.statement": "Assumption to monitor",
    "assumptions.0.entityId": "Entity ID",
    "assumptions.0.predicate": "Predicate",
    "assumptions.0.expectedValue": "Expected by",
  };
  const messages = detail.flatMap((item: unknown) => {
    if (!item || typeof item !== "object" || !("msg" in item) || typeof item.msg !== "string") return [];
    const path = "loc" in item && Array.isArray(item.loc)
      ? item.loc.filter((part: unknown) => part !== "body").join(".") : "";
    return [`${fieldNames[path] ?? (path || "Decision")}: ${item.msg}`];
  });
  return messages.length ? messages.join("; ") : fallback;
}

export async function createLiveDecision(projectId: string, body: unknown): Promise<LiveDecision> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/decisions`, {
    method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => ({}));
    throw new Error(decisionErrorMessage(payload, `Decision draft failed with status ${response.status}.`));
  }
  const result: { decision: LiveDecision } = await response.json();
  return result.decision;
}

export async function confirmLiveDecision(projectId: string, decision: LiveDecision): Promise<LiveDecision> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/decisions/${encodeURIComponent(decision.id)}/confirm`, {
    method: "POST", headers: { "Idempotency-Key": crypto.randomUUID(), "If-Match": `"${decision.version}"` },
  });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => ({}));
    throw new Error(decisionErrorMessage(payload, `Decision confirmation failed with status ${response.status}.`));
  }
  const result: { decision: LiveDecision } = await response.json();
  return result.decision;
}

export async function listMonitoredAssumptions(projectId: string): Promise<MonitoredAssumption[]> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/decisions/monitored`);
  if (!response.ok) throw new Error(`Monitored decisions failed with status ${response.status}.`);
  return response.json();
}

export async function extractSource(projectId: string, sourceId: string, assumptionId: string, entityAlias: string, predicateAlias: string): Promise<ExtractionResult> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(sourceId)}/extract`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ assumption_id: assumptionId, entity_alias: entityAlias, predicate_alias: predicateAlias }),
  });
  if (!response.ok) {
    const payload: { detail?: string } = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Extraction failed with status ${response.status}.`);
  }
  return response.json();
}

export async function getExtraction(projectId: string, sourceId: string): Promise<ExtractionResult | null> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(sourceId)}/extraction`);
  if (response.status === 404 || response.status === 409) return null;
  if (!response.ok) throw new Error(`Extraction lookup failed with status ${response.status}.`);
  return response.json();
}

export async function getAssessmentResults(projectId: string): Promise<AssessmentResults> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/assessments/results`);
  if (!response.ok) throw new Error(`Assessment results failed with status ${response.status}.`);
  return response.json();
}

export async function runAssessment(projectId: string): Promise<void> {
  const response = await fetchPrivateApi(`/api/v1/projects/${encodeURIComponent(projectId)}/assessments`, {
    method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify({ reason: "Manual project review" }),
  });
  if (!response.ok) {
    const payload: { detail?: string } = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Assessment failed with status ${response.status}.`);
  }
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

export async function submitAnalysisJob(projectId: string): Promise<BackgroundJob> {
  return jobResponse(await fetchPrivateApi(
    `/api/v1/projects/${encodeURIComponent(projectId)}/jobs/analysis`, { method: "POST" },
  ));
}

export async function submitRefreshJob(projectId: string, folderId: string): Promise<BackgroundJob> {
  return jobResponse(await fetchPrivateApi(
    `/api/v1/projects/${encodeURIComponent(projectId)}/jobs/refresh`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ folder_id: folderId }) },
  ));
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
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload && typeof payload.detail === "string" ? payload.detail : null;
    throw new Error(detail ?? `Drive disconnect failed with status ${response.status}.`);
  }
}

export async function checkBackendHealth(): Promise<HealthResponse> {
  const res = await fetch("/api/v1/health", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}: ${res.statusText}`);
  }
  return res.json();
}
