import { AppShell } from "@/components/app-shell";
import { AuthGate } from "@/components/auth/auth-gate";

export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const judgeWorkspace = Boolean(process.env.DEMO_PROJECT_ID && id === process.env.DEMO_PROJECT_ID);
  return <AuthGate demoProjectId={judgeWorkspace ? id : null}><AppShell projectId={id}>
    {judgeWorkspace && <aside className="notice judge-guide" aria-label="Demo workspace guide">
      <strong>Connected demo · sample project data</strong>
      <p>Start in Connections and refresh the configured folder. In Decisions, create and confirm a test decision using “Decision record - Acme launch” and the original October 15, 2026 deadline (entity: vendor_acme, predicate: delivery_date). In Sources, extract the Acme Logistics delivery date from the vendor update. In Reviews, run an assessment to see the October 24 delay, then record your response.</p>
      <p>You can create, confirm, and archive test decisions. This shared workspace retains changes between visits. Drive connection settings are managed by the app owner.</p>
    </aside>}
    {children}</AppShell></AuthGate>;
}
