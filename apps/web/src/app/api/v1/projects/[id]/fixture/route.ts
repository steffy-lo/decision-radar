import { NextResponse } from "next/server";
import { demoFixture } from "@/lib/demo/fixture.server";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (id !== demoFixture.projectId) {
    return NextResponse.json({ error: "Fixture project not found" }, { status: 404 });
  }
  return NextResponse.json(demoFixture, {
    headers: { "Cache-Control": "private, no-store" },
  });
}
