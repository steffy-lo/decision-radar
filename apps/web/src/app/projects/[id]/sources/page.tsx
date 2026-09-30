import { SourcesWorkspace } from "@/components/evidence-workspace";
import { DriveConnectionPanel } from "@/components/connections/drive-connection-panel";

export default async function SourcesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SourcesWorkspace projectId={id} connectionControl={<DriveConnectionPanel projectId={id} />} />;
}
