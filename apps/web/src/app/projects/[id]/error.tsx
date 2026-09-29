"use client";

import { EmptyState } from "@/components/ui";

export default function ProjectError({ reset }: { reset: () => void }) {
  return (
    <EmptyState
      title="This page could not be opened"
      description="Please try again. Your project data has not been changed."
      action={<button className="button button--secondary" type="button" onClick={reset}>Try again</button>}
    />
  );
}
