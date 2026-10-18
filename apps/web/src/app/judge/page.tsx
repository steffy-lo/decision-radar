import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default function JudgePage() {
  const projectId = process.env.JUDGE_PROJECT_ID;
  if (!projectId) return <main className="auth-page"><section className="auth-page__card"><h1>Connected demo is being prepared</h1><p>Ask the app owner for the judge workspace link and credentials.</p></section></main>;
  redirect(`/projects/${encodeURIComponent(projectId)}/connections`);
}
