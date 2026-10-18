import type { Metadata } from "next";
import { ConnectionSetupWorkspace } from "@/components/connections/connection-setup-workspace";
import { JobStatusPanel } from "@/components/jobs/job-status-panel";

export const metadata: Metadata = { title: "Connections | Decision Radar" };

export default async function ConnectionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <><ConnectionSetupWorkspace projectId={id} /><div className="mt-6"><JobStatusPanel projectId={id} /></div></>;
}
