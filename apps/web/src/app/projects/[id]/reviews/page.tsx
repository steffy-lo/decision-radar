import { ReviewsWorkspace } from "@/components/evidence-workspace";

export default async function ReviewsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReviewsWorkspace projectId={id} />;
}
