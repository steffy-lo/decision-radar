import type { Metadata } from "next";
import { ReviewsWorkspace } from "@/components/evidence-workspace";

export const metadata: Metadata = { title: "Reviews | Decision Radar" };

export default async function ReviewsPage({ params, searchParams }: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ alertId?: string | string[] }>;
}) {
  const { id } = await params;
  const query = await searchParams;
  const alertId = typeof query.alertId === "string" ? query.alertId : undefined;
  return <ReviewsWorkspace projectId={id} alertId={alertId} />;
}
