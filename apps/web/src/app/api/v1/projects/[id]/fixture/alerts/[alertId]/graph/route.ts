import { NextResponse } from "next/server";
import { demoImpact as demoGraph } from "@/lib/demo/fixture.server";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string; alertId: string }> }) {
  const { id, alertId } = await params;
  if (id !== demoGraph.projectId || alertId !== demoGraph.alertId) {
    return NextResponse.json({ detail: "Demo impact not found." }, { status: 404 });
  }
  return NextResponse.json(demoGraph, { headers: { "Cache-Control": "private, no-store", ETag: `"${demoGraph.revision}"` } });
}
