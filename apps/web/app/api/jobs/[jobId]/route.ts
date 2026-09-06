import { NextResponse } from "next/server";
import { CampaignForgeApiError, getJob } from "@/lib/campaignforge-api";

export async function GET(_request: Request, { params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  try { return NextResponse.json(await getJob(jobId), { headers: { "Cache-Control": "no-store" } }); }
  catch (error) { const status = error instanceof CampaignForgeApiError ? error.status : 500; return NextResponse.json({ error: error instanceof Error ? error.message : "Could not load job." }, { status }); }
}
