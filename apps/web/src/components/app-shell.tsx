"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { isDemoProject } from "@/lib/demo/use-project-data";

const items = [
  { slug: "connections", label: "Connections", icon: "⛓" },
  { slug: "decisions", label: "Decisions", icon: "◈" },
  { slug: "sources", label: "Sources", icon: "▤" },
  { slug: "reviews", label: "Reviews", icon: "◎" },
  { slug: "briefs", label: "Briefs", icon: "▧" },
] as const;

export function AppShell({
  projectId,
  children,
}: {
  projectId: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const base = `/projects/${encodeURIComponent(projectId)}`;
  const demo = isDemoProject(projectId);

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Project navigation">
        <Link className="brand" href="/">
          <span className="brand__mark" aria-hidden="true"><span /></span>
          <span className="brand__wordmark">Decision<span>Radar</span></span>
        </Link>

        <div className="sidebar__section-label">WORKSPACE</div>
        <nav className="sidebar__nav" aria-label="Primary">
          {items.filter((item) => !demo || item.slug !== "connections").map((item) => {
            const href = `${base}/${item.slug}`;
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                href={href}
                className={`nav-link ${active ? "nav-link--active" : ""}`}
                aria-current={active ? "page" : undefined}
                key={item.slug}
              >
                <span className="nav-link__icon" aria-hidden="true">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar__bottom">
          <div className="sidebar__insight">
            <span className="sidebar__insight-icon" aria-hidden="true">✳</span>
            <strong>Context, connected.</strong>
            <p>See what changed and what it means for every decision.</p>
          </div>
          <div className="sidebar__footer">
            <span className="sidebar__footer-avatar" aria-hidden="true">D</span>
            <span><strong>{demo ? "Demo workspace" : "Project workspace"}</strong><small>{demo ? "Synthetic project data" : "Connected project data"}</small></span>
          </div>
        </div>
      </aside>

      <div className="app-shell__main">
        <header className="topbar">
          <div className="topbar__crumbs"><span>Workspace</span><span aria-hidden="true">/</span><strong>{demo ? "Launch readiness" : "Project workspace"}</strong></div>
          <div className="topbar__right">
            {demo && <span className="demo-badge"><span aria-hidden="true" /> Fixture mode</span>}
            <span className="topbar__avatar" aria-label={demo ? "Demo user" : "Signed-in user"}>D</span>
          </div>
        </header>
        <nav className="mobile-nav" aria-label="Mobile project navigation">
          {items.filter((item) => !demo || item.slug !== "connections").map((item) => {
            const href = `${base}/${item.slug}`;
            return <Link href={href} aria-current={pathname === href ? "page" : undefined} key={item.slug}>{item.label}</Link>;
          })}
        </nav>
        <main className="page-content" id="main-content" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}
