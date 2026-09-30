import type { EvidenceRef } from "@/lib/domain/models";

function safeSourceUrl(value: string): string | null {
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

export function EvidenceReference({ evidence, label, available = true, sourceType }: {
  evidence: EvidenceRef;
  label: string;
  available?: boolean;
  sourceType?: string;
}) {
  if (!available) {
    return <div className="evidence-reference evidence-reference--unavailable">
      <span className="section-kicker">{label}</span>
      <strong>Source access unavailable</strong>
      <p>The source cannot be opened right now. Its quote and details are hidden until access is restored.</p>
    </div>;
  }

  const href = safeSourceUrl(evidence.nativeUrl);
  return <div className="evidence-reference">
    <span className="section-kicker">{label}</span>
    <blockquote>“{evidence.quote}”</blockquote>
    <div className="evidence-reference__footer">
      <span>{evidence.sourceTitle}{sourceType ? ` · ${sourceType.includes("google-apps.document") ? "Google Doc" : sourceType.startsWith("text/") ? "Text file" : "Source file"}` : ""}</span>
      {href && <a className="text-link" href={href} target="_blank" rel="noopener noreferrer" aria-label={`Open ${evidence.sourceTitle} in Google Drive`}>Open source ↗</a>}
    </div>
  </div>;
}
