import type { Metadata } from "next";
import { DecisionRegister } from "@/components/decision-register";

export const metadata: Metadata = { title: "Decisions | Decision Radar" };

export default async function DecisionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DecisionRegister projectId={id} />;
}
