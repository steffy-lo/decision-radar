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
  return <AuthGate><AppShell projectId={id}>{children}</AppShell></AuthGate>;
}
