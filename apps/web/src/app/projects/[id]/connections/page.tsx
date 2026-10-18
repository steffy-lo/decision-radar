import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { isDemoProject } from "@/lib/demo/project";
import { ConnectionSetupWorkspace } from "@/components/connections/connection-setup-workspace";
import { JobStatusPanel } from "@/components/jobs/job-status-panel";

export const metadata: Metadata = { title: "Connections | Decision Radar" };

export default async function ConnectionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (isDemoProject(id)) redirect(`/projects/${encodeURIComponent(id)}/sources`);
  return <><ConnectionSetupWorkspace projectId={id} /><div className="mt-6"><JobStatusPanel projectId={id} /></div></>;
}
