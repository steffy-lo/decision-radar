import type { Metadata } from "next";
import { WorkspaceLogin } from "@/components/auth/workspace-login";

export const metadata: Metadata = { title: "Google sign-in | Decision Radar" };

export default function LoginPage() {
  return <WorkspaceLogin />;
}
