"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, BookOpen, Boxes, Cable, LayoutDashboard, Megaphone, Menu, Settings, Sparkles, X } from "lucide-react";
import { useState } from "react";

const links = [
  ["Dashboard", "/", LayoutDashboard],
  ["Campaigns", "/campaigns/autumn-launch", Megaphone],
  ["Analytics", "/analytics", BarChart3],
  ["Brand kits", "/brand-kits", BookOpen],
  ["Integrations", "/integrations", Cable],
  ["Settings", "/settings", Settings],
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <div className="app-shell">
      <header className="mobile-header">
        <Brand />
        <button className="icon-button" aria-label="Toggle navigation" onClick={() => setOpen(!open)}>
          {open ? <X /> : <Menu />}
        </button>
      </header>
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`} aria-label="Primary navigation">
        <Brand />
        <nav>
          <p className="eyebrow nav-label">Workspace</p>
          {links.map(([label, href, Icon]) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href.split("/").slice(0, 2).join("/"));
            return (
              <Link key={href} href={href} className={`nav-link ${active ? "nav-link-active" : ""}`} onClick={() => setOpen(false)}>
                <Icon aria-hidden="true" /> <span>{label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="usage-block">
            <div className="usage-title"><Sparkles aria-hidden="true" /> AI usage</div>
            <div className="usage-track"><span style={{ width: "34%" }} /></div>
            <small>£6.80 of £20 monthly cap</small>
          </div>
          <div className="profile-row">
            <span className="avatar">TM</span>
            <span><strong>Tim&apos;s workspace</strong><small>Owner</small></span>
          </div>
        </div>
      </aside>
      <main id="main-content">{children}</main>
    </div>
  );
}

function Brand() {
  return <Link href="/" className="brand"><span className="brand-mark"><Boxes /></span><span>CampaignForge <b>AI</b></span></Link>;
}
