/** Explain the first action needed before a document can be extracted. */
export function extractionBlocker(input: {
  loading: boolean;
  role?: string;
  assumption: boolean;
  source?: { status: string; monitoring_paused?: boolean };
  subject: string;
  detail: string;
  busy: boolean;
}): string | null {
  if (input.busy) return "Gemini is reading the update. Keep this page open; results will appear below.";
  if (input.loading) return "Loading your requirements and documents…";
  if (!input.role) return "Your access could not be checked. Reload the page to try again.";
  if (input.role === "viewer") return "You have view-only access. Ask a project editor to extract facts.";
  if (!input.assumption) return "Choose a requirement from a confirmed decision.";
  if (!input.source) return "Choose the document containing the update.";
  if (input.source.monitoring_paused) return "Monitoring is paused for this document. Resume it in Connections first.";
  if (input.source.status !== "ready") return "This document is not ready. Refresh Drive above and check its status in Connected sources.";
  if (!input.subject.trim()) return "Enter who or what the update is about, using the name in the document.";
  if (!input.detail.trim()) return "Enter the information to look for, such as delivery date.";
  return null;
}

export function extractionHelp(reason: string): string {
  if (reason.includes("entity") && reason.includes("unresolved")) return "The name in the update could not be matched to your requirement. Check the name you entered, then extract again.";
  if (reason.includes("predicate") && reason.includes("unresolved")) return "The information in the update could not be matched to your requirement. Check your description, such as delivery date, then extract again.";
  if (reason.includes("tentative")) return "The update describes a possibility rather than a commitment. Confirm the information in the document, refresh Drive, then extract again.";
  if (reason.includes("negated")) return "It is unclear whether the update says this will happen. Clarify the wording in the document, refresh Drive, then extract again.";
  if (reason.includes("context")) return "The update does not include enough context to verify this fact. Add the missing details, refresh Drive, then extract again.";
  if (reason.includes("value") || reason.includes("quote")) return "The supporting quote does not clearly show the value. Include the full value in the document, including the year for a date, refresh Drive, then extract again.";
  return "This information could not be verified. Check the supporting quote and matching phrases before extracting again.";
}
