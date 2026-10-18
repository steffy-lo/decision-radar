import type { Metadata } from "next";
import { DemoEntry } from "@/components/auth/demo-entry";

export const metadata: Metadata = { title: "Connected demo | Decision Radar" };
export const dynamic = "force-dynamic";

export default function DemoPage() {
  const projectId = process.env.DEMO_PROJECT_ID;
  if (!projectId) return <main className="auth-page"><section className="auth-page__card"><h1>Connected demo is being prepared</h1><p>Please try again later.</p></section></main>;
  return <DemoEntry projectId={projectId} email="demo@decision-radar.example" />;
}
