export interface HealthResponse {
  status: string;
  service: string;
  timestamp: string;
  environment: string;
}

export async function checkBackendHealth(): Promise<HealthResponse> {
  const res = await fetch("/api/v1/health", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}: ${res.statusText}`);
  }
  return res.json();
}
