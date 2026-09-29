import { SourcesWorkspace } from "@/components/evidence-workspace";

export default async function SourcesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SourcesWorkspace projectId={id} />;
}
