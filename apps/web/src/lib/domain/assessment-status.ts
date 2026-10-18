interface AssessmentSummary {
  findingCount: number;
  coverage: { state: string }[];
}

export function assessmentStatus(run: AssessmentSummary | null, alertCount: number, hasDrift = false): { title: string; description: string } {
  if (!run) return { title: "No assessment yet", description: "Confirm a decision, extract facts from an update, then run an assessment." };
  if (!run.findingCount && !run.coverage.length) return { title: "Nothing was assessed", description: "This run had no active monitored assumptions to compare. It does not establish whether your documents agree. Confirm a decision and extract facts before trying again." };
  if (alertCount) return { title: "Decisions need review", description: "New evidence challenges a monitored requirement. Compare the quotes and decide what to do." };
  if (hasDrift || run.coverage.some((row) => row.state !== "assessed")) return { title: "Evidence unclear", description: "Some assumptions could not be assessed. Resolve the coverage gaps before drawing a conclusion." };
  return { title: "No conflict in the comparisons made", description: "Verified facts did not contradict the monitored assumptions in this run. This result applies only to the evidence and requirements assessed." };
}
