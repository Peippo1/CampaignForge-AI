import { AppShell } from "@/components/app-shell";

export default function CampaignsLoading() {
  return <AppShell><div className="page" aria-busy="true" aria-label="Loading campaigns"><div className="skeleton skeleton-title" /><div className="skeleton skeleton-form" /><div className="campaign-grid"><div className="skeleton skeleton-card" /><div className="skeleton skeleton-card" /></div></div></AppShell>;
}
