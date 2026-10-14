import type { Metadata } from "next";
import { BriefsWorkspace } from "@/components/briefs-workspace";

export const metadata: Metadata = { title: "Briefs | Decision Radar" };

export default async function BriefsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <BriefsWorkspace projectId={id} />;
}
