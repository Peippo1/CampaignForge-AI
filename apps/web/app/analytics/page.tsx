import { AppShell } from "@/components/app-shell";
import { PerformanceChart } from "@/components/performance-chart";

export default function AnalyticsPage() {
  return <AppShell><div className="page"><header className="page-header"><div><p className="eyebrow">Platform-reported results</p><h1>Campaign analytics</h1><p>Google Ads and Meta Ads remain separate to avoid false cross-platform attribution.</p></div><button className="button secondary">Last 30 days</button></header><section className="metric-grid"><Metric label="Spend" value="£24,860"/><Metric label="Clicks" value="18,420"/><Metric label="Conversions" value="742"/><Metric label="ROAS" value="3.8×"/></section><section className="panel"><div className="panel-heading"><div><p className="eyebrow">Reach</p><h2>Daily platform trend</h2></div><span className="badge neutral">GBP · Europe/London</span></div><PerformanceChart /></section></div></AppShell>;
}

function Metric({label,value}:{label:string;value:string}) { return <article className="metric-card"><p>{label}</p><strong>{value}</strong><small>Platform reported</small></article>; }
