import type { Metadata } from "next";
import { SourcesWorkspace } from "@/components/evidence-workspace";
import { JobStatusPanel } from "@/components/jobs/job-status-panel";
import { demoFixture } from "@/lib/demo/fixture.server";

export const metadata: Metadata = { title: "Sources | Decision Radar" };

export default async function SourcesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <><SourcesWorkspace projectId={id} />{id !== demoFixture.projectId && <JobStatusPanel key={id} projectId={id} />}</>;
}
