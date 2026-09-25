import { NextRequest, NextResponse } from "next/server";

const TARGET_API_HOST = process.env.RADAR_API_URL || "http://127.0.0.1:8000";

/**
 * Proxies incoming API requests from Next.js (`/api/v1/*`) to the backend FastAPI service.
 *
 * Handles URL target construction, query string preservation, header forwarding,
 * request body streaming, and error handling for unreachable backend instances.
 * Prevents CORS restrictions by serving requests from the same origin as the frontend.
 *
 * @param request - The incoming Next.js HTTP request.
 * @param context - Dynamic route context containing promised path parameters.
 * @returns Next.js response forwarding the backend payload or a 502 Bad Gateway response on failure.
 */
async function proxyRequest(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  const path = resolvedParams.path ? resolvedParams.path.join("/") : "";
  const targetUrl = new URL(`/api/v1/${path}`, TARGET_API_HOST);

  // Preserve query string
  targetUrl.search = request.nextUrl.search;

  // Prepare headers
  const headers = new Headers(request.headers);
  headers.set("host", new URL(TARGET_API_HOST).host);

  try {
    const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer();

    const response = await fetch(targetUrl.toString(), {
      method: request.method,
      headers: headers,
      body: body,
      cache: "no-store",
    });

    const responseHeaders = new Headers(response.headers);

    return new NextResponse(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("[API Proxy Error]: Failed to reach FastAPI backend:", error);
    return NextResponse.json(
      {
        error: "Bad Gateway",
        message: `Unable to connect to backend service at ${TARGET_API_HOST}`,
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 502 }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
export const PATCH = proxyRequest;
