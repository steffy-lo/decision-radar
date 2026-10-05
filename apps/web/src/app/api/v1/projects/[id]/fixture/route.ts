import { NextResponse } from "next/server";
import { accessUnavailableFixture, demoFixture, evidenceUnclearFixture, noDetectedIssueFixture } from "@/lib/demo/fixture.server";

export const runtime = "nodejs";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (id !== demoFixture.projectId) {
    return NextResponse.json({ error: "Fixture project not found" }, { status: 404 });
  }
  const scenario = new URL(request.url).searchParams.get("scenario");
  if (scenario && !["access-unavailable", "evidence-unclear", "no-detected-issue"].includes(scenario)) {
    return NextResponse.json({ error: "Unknown fixture scenario" }, { status: 400 });
  }
  const fixture = scenario === "access-unavailable" ? accessUnavailableFixture
    : scenario === "evidence-unclear" ? evidenceUnclearFixture
    : scenario === "no-detected-issue" ? noDetectedIssueFixture : demoFixture;
  return NextResponse.json(fixture, {
    headers: { "Cache-Control": "private, no-store" },
  });
}
