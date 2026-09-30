import { EmptyState, PageHeading } from "@/components/ui";

export default function BriefsPage() {
  return (
    <>
      <PageHeading eyebrow="DECISION SUMMARIES" title="Briefs" description="A concise record of decisions, changes, and human review." />
      <EmptyState title="No briefs yet" description="A summary can be prepared after the team reviews a decision." />
    </>
  );
}
