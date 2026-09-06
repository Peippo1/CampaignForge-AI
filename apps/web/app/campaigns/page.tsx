import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { CreateCampaignForm } from "@/components/create-campaign-form";
import { Campaign, CampaignForgeApiError, listCampaigns } from "@/lib/campaignforge-api";
import { ArrowRight, Megaphone } from "lucide-react";

export const dynamic = "force-dynamic";

const stageLabels: Record<string, string> = { draft: "Brief", strategy_ready: "Strategy review", strategy_approved: "Copy next", copy_ready: "Copy review", copy_approved: "Creative next", image_generation_approved: "Generating assets", assets_ready: "Asset review", final_approved: "Approved" };

export default async function CampaignsPage() {
  let campaigns: Campaign[] = [];
  let loadError = "";
  try { campaigns = await listCampaigns(); } catch (error) { loadError = error instanceof CampaignForgeApiError ? error.message : "The campaign service is unavailable."; }
  return <AppShell><div className="page"><header className="page-header"><div><p className="eyebrow">Campaign operations</p><h1>Campaigns</h1><p>Create, review and move every campaign through one governed workflow.</p></div></header><CreateCampaignForm />{loadError ? <section className="empty-card service-state"><span><Megaphone /></span><h2>Connect the campaign API</h2><p>{loadError} Start FastAPI on port 8000 or configure CAMPAIGNFORGE_API_URL.</p></section> : campaigns.length === 0 ? <section className="empty-card"><span><Megaphone /></span><h2>Your first campaign starts here</h2><p>Create a campaign above, then use the low-cost local agent to draft its strategy.</p></section> : <section className="campaign-grid" aria-label="Campaign list">{campaigns.map((campaign) => <Link className="campaign-card" href={`/campaigns/${campaign.campaign_id}`} key={campaign.campaign_id}><div><span className={`badge ${campaign.stage.includes("ready") ? "warning" : campaign.export_enabled ? "success" : "neutral"}`}>{stageLabels[campaign.stage] || campaign.stage}</span><h2>{campaign.title}</h2><p>Revision {campaign.revision} · {campaign.approvals.length} approvals</p></div><ArrowRight aria-hidden="true" /></Link>)}</section>}</div></AppShell>;
}
