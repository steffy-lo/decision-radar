import { NextResponse } from "next/server";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parseDemoFixture } from "@/lib/domain/models";

export const runtime = "nodejs";

const demo = parseDemoFixture(JSON.parse(
  readFileSync(resolve(process.cwd(), "../../fixtures/vendor-delay.json"), "utf8"),
));

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (id !== demo.projectId) {
    return NextResponse.json({ error: "Fixture project not found" }, { status: 404 });
  }
  return NextResponse.json(demo, {
    headers: { "Cache-Control": "private, no-store" },
  });
}
