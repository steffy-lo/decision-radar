import { NextRequest, NextResponse } from "next/server";
import { cloudRunIdentityHeader } from "@/lib/server/cloud-run-identity";

const TARGET_API_HOST = process.env.RADAR_API_URL || "http://127.0.0.1:8000";

// Workspace responses may contain private project data and must not be cached.
const PRIVATE_RESPONSE_CACHE_CONTROL = "private, no-store";
const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "accept-language",
  "authorization",
  "content-type",
  "idempotency-key",
  "if-match",
] as const;
const FORWARDED_RESPONSE_HEADERS = ["content-type", "etag", "retry-after", "set-cookie", "www-authenticate"] as const;

/**
 * Proxies private same-origin API requests to the FastAPI service.
 */
async function proxyRequest(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  const pathParts = resolvedParams.path ?? [];
  const path = pathParts.map(encodeURIComponent).join("/");
  const targetUrl = new URL(`/api/v1/${path}`, TARGET_API_HOST);
  targetUrl.search = request.nextUrl.search;

  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  try {
    const serviceIdentity = await cloudRunIdentityHeader();
    if (serviceIdentity) headers.set("X-Serverless-Authorization", serviceIdentity);
    const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer();

    const response = await fetch(targetUrl.toString(), {
      method: request.method,
      headers: headers,
      body: body,
      cache: "no-store",
    });

    const responseHeaders = new Headers({ "Cache-Control": PRIVATE_RESPONSE_CACHE_CONTROL });
    for (const name of FORWARDED_RESPONSE_HEADERS) {
      const value = response.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new NextResponse(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("[API Proxy Error]: Failed to reach FastAPI backend:", error);
    return privateJson({ detail: "Unable to reach the API service." }, 502);
  }
}

function privateJson(body: unknown, status: number) {
  return NextResponse.json(body, {
    status,
    headers: { "Cache-Control": PRIVATE_RESPONSE_CACHE_CONTROL },
  });
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
export const PATCH = proxyRequest;
