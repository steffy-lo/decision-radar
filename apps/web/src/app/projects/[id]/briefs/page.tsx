import { BriefsWorkspace } from "@/components/briefs-workspace";

export default async function BriefsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <BriefsWorkspace projectId={id} />;
}
