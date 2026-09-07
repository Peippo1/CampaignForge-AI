import { AppShell } from "@/components/app-shell";
import { CampaignWorkspace } from "@/components/campaign-workspace";
import { getCampaign, listBrandKits } from "@/lib/campaignforge-api";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function CampaignPage({ params }: { params: Promise<{ campaignId: string }> }) {
  const { campaignId } = await params;
  const [campaign, brandKits] = await Promise.all([loadCampaign(campaignId), listBrandKits()]);
  return <AppShell><CampaignWorkspace key={`${campaign.campaign_id}:${campaign.stage}`} campaign={campaign} brandKits={brandKits} /></AppShell>;
}

async function loadCampaign(campaignId: string) {
  try {
    return await getCampaign(campaignId);
  } catch (error) {
    if (error instanceof Error && error.message === "Resource not found.") notFound();
    throw error;
  }
}
