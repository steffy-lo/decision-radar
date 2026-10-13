import { BriefDetailWorkspace } from "@/components/briefs-workspace";

export default async function BriefPage({ params }: { params: Promise<{ id: string; briefId: string }> }) {
  const { id, briefId } = await params;
  return <BriefDetailWorkspace projectId={id} briefId={briefId} />;
}
