import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Decision Radar",
  description: "A clear view of the decisions behind every project.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
