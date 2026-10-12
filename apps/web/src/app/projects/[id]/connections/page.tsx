import { ConnectionSetupWorkspace } from "@/components/connections/connection-setup-workspace";
import { JobStatusPanel } from "@/components/jobs/job-status-panel";

export default async function ConnectionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <><ConnectionSetupWorkspace projectId={id} /><JobStatusPanel projectId={id} /></>;
}
