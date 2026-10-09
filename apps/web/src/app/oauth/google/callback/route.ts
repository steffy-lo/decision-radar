import { NextRequest, NextResponse } from "next/server";
import { cloudRunIdentityHeader } from "@/lib/server/cloud-run-identity";
import { publicCallbackUrl } from "@/lib/server/public-callback-url";

const TARGET_API_HOST = process.env.RADAR_API_URL || "http://127.0.0.1:8000";
const OAUTH_NONCE_COOKIE = "drive_oauth_nonce";

function callbackRedirect(request: NextRequest, path: string) {
  let destination: URL;
  try {
    destination = publicCallbackUrl(
      path, request.url, process.env.RADAR_WEB_ORIGIN,
      process.env.NODE_ENV === "production",
    );
  } catch {
    return NextResponse.json({ error: "Public web origin is not configured." }, { status: 503 });
  }
  const response = NextResponse.redirect(destination);
  response.cookies.set(OAUTH_NONCE_COOKIE, "", {
    httpOnly: true,
    maxAge: 0,
    path: "/oauth/google/callback",
    sameSite: "lax",
    secure: request.nextUrl.protocol === "https:",
  });
  return response;
}

/**
 * Google redirects here with a short-lived authorization code. The Next.js
 * server forwards it to FastAPI so neither the code nor a Drive token enters
 * browser JavaScript.
 */
export async function GET(request: NextRequest) {
  const callbackUrl = new URL("/api/v1/oauth/google/callback", TARGET_API_HOST);
  callbackUrl.search = request.nextUrl.search;

  try {
    const headers = new Headers();
    const cookie = request.headers.get("cookie");
    if (cookie) headers.set("cookie", cookie);
    const serviceIdentity = await cloudRunIdentityHeader();
    if (serviceIdentity) headers.set("X-Serverless-Authorization", serviceIdentity);

    const response = await fetch(callbackUrl, { cache: "no-store", headers });
    if (!response.ok) {
      const reason = response.status === 503 ? "storage_unavailable" : "authorization_failed";
      return callbackRedirect(request, `/?connection=failed&reason=${reason}`);
    }

    const result = (await response.json()) as { project_id: string };
    return callbackRedirect(
      request,
      `/projects/${encodeURIComponent(result.project_id)}/sources?connection=active`,
    );
  } catch {
    return callbackRedirect(request, "/?connection=failed");
  }
}
