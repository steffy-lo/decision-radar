import { DecisionRegister } from "@/components/decision-register";

export default async function DecisionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DecisionRegister projectId={id} />;
}
