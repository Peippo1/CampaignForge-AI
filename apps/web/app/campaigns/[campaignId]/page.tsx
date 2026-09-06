import { AppShell } from "@/components/app-shell";
import { CampaignWorkspace } from "@/components/campaign-workspace";

export default async function CampaignPage({ params }: { params: Promise<{ campaignId: string }> }) {
  const { campaignId } = await params;
  return <AppShell><CampaignWorkspace campaignId={campaignId} /></AppShell>;
}
