import { ArrowUpRight, Clock3, CircleAlert, CircleCheck, Plus, Sparkles } from "lucide-react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { PerformanceChart } from "@/components/performance-chart";
import { campaigns } from "@/lib/demo-data";

export default function DashboardPage() {
  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div><p className="eyebrow">Monday, 6 September</p><h1>Good morning, Tim</h1><p>Four campaigns are moving. Two need a reviewer.</p></div>
          <Link className="button primary" href="/campaigns/autumn-launch"><Plus /> New campaign</Link>
        </header>
        <section className="metric-grid" aria-label="Workspace summary">
          <Metric label="Active campaigns" value="12" note="3 launched this month" icon={<Sparkles />} />
          <Metric label="Pending approvals" value="2" note="Oldest waiting 4 hours" icon={<Clock3 />} accent />
          <Metric label="Successful runs" value="96.4%" note="142 agent runs this month" icon={<CircleCheck />} />
          <Metric label="Media efficiency" value="3.8×" note="Platform-reported ROAS" icon={<ArrowUpRight />} />
        </section>
        <section className="dashboard-grid">
          <div className="panel chart-panel">
            <div className="panel-heading"><div><p className="eyebrow">Performance</p><h2>Reach by platform</h2></div><span className="badge success">+14.2% this week</span></div>
            <PerformanceChart />
          </div>
          <aside className="panel review-panel">
            <div className="panel-heading"><div><p className="eyebrow">Review queue</p><h2>Needs your eye</h2></div><span className="count">2</span></div>
            <ReviewItem title="Agency partner series" detail="3 visual concepts" age="48 min" />
            <ReviewItem title="Autumn product launch" detail="Copy and CTAs" age="4 hr" />
            <Link className="text-link" href="/campaigns/autumn-launch">Open review queue <ArrowUpRight /></Link>
          </aside>
        </section>
        <section className="panel campaign-table-panel">
          <div className="panel-heading"><div><p className="eyebrow">Campaign pipeline</p><h2>Recent work</h2></div><Link className="text-link" href="/campaigns/autumn-launch">View all <ArrowUpRight /></Link></div>
          <div className="table-wrap"><table><thead><tr><th>Campaign</th><th>Stage</th><th>Owner</th><th>Updated</th><th>Status</th></tr></thead><tbody>{campaigns.map((campaign) => <tr key={campaign.name}><td><Link href="/campaigns/autumn-launch">{campaign.name}</Link></td><td>{campaign.stage}</td><td>{campaign.owner}</td><td>{campaign.updated}</td><td><span className={`status-dot ${campaign.health === "Needs review" ? "warning" : ""}`} />{campaign.health}</td></tr>)}</tbody></table></div>
        </section>
      </div>
    </AppShell>
  );
}

function Metric({ label, value, note, icon, accent = false }: { label: string; value: string; note: string; icon: React.ReactNode; accent?: boolean }) {
  return <article className={`metric-card ${accent ? "metric-accent" : ""}`}><div className="metric-icon">{icon}</div><p>{label}</p><strong>{value}</strong><small>{note}</small></article>;
}

function ReviewItem({ title, detail, age }: { title: string; detail: string; age: string }) {
  return <div className="review-item"><span className="review-icon"><CircleAlert /></span><div><strong>{title}</strong><p>{detail}</p></div><time>{age}</time></div>;
}
