"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { Campaign, AgentJob, BrandKit, campaignForgeFetch } from "@/lib/campaignforge-api";
import type { ActionState } from "@/lib/action-state";

function text(formData: FormData, field: string, maxLength: number): string {
  const value = String(formData.get(field) || "").trim();
  if (!value || value.length > maxLength) throw new Error(`${field.replaceAll("_", " ")} is required and must be under ${maxLength} characters.`);
  return value;
}

function lines(formData: FormData, field: string): string[] {
  return String(formData.get(field) || "").split(/\n|,/).map((value) => value.trim()).filter(Boolean);
}

export async function createCampaignAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  let campaign: Campaign;
  try {
    campaign = await campaignForgeFetch<Campaign>("/v1/campaigns", {
      method: "POST",
      body: JSON.stringify({ title: text(formData, "title", 120) }),
      idempotencyKey: text(formData, "idempotency_key", 80),
    });
  } catch (error) {
    return { status: "error", message: error instanceof Error ? error.message : "Could not create campaign." };
  }
  revalidatePath("/campaigns");
  redirect(`/campaigns/${campaign.campaign_id}`);
}

export async function createBrandKitAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  try {
    await campaignForgeFetch<BrandKit>("/v1/brand-kits", {
      method: "POST",
      body: JSON.stringify({
        name: text(formData, "name", 160),
        voice: text(formData, "voice", 4000),
        audiences: lines(formData, "audiences"),
        product_facts: lines(formData, "product_facts"),
        required_phrases: lines(formData, "required_phrases"),
        banned_terms: lines(formData, "banned_terms"),
        compliance_rules: lines(formData, "compliance_rules"),
      }),
    });
  } catch (error) {
    return { status: "error", message: error instanceof Error ? error.message : "Could not create brand kit." };
  }
  revalidatePath("/brand-kits");
  return { status: "success", message: "Brand kit created." };
}

export async function runAgentAction(campaignId: string, _state: ActionState, formData: FormData): Promise<ActionState> {
  try {
    const job = await campaignForgeFetch<AgentJob>(`/v1/campaigns/${encodeURIComponent(campaignId)}/runs`, {
      method: "POST",
      body: JSON.stringify({ kind: String(formData.get("kind") || "strategy"), instructions: text(formData, "instructions", 4000) }),
      idempotencyKey: text(formData, "idempotency_key", 80),
    });
    if (process.env.NODE_ENV !== "production" || process.env.CAMPAIGNFORGE_WEB_AUTH_MODE === "development") {
      await campaignForgeFetch<void>("/v1/internal/jobs/dispatch", {
        method: "POST",
        body: JSON.stringify({ job_id: job.job_id, workspace_id: job.workspace_id }),
      });
    }
    return { status: "success", message: "Agent run queued. Local runs use the free deterministic adapter.", jobId: job.job_id };
  } catch (error) {
    return { status: "error", message: error instanceof Error ? error.message : "Could not start the agent." };
  }
}

export async function approveCampaignStageAction(campaignId: string, stage: "strategy" | "copy" | "final"): Promise<void> {
  await campaignForgeFetch<Campaign>(`/v1/campaigns/${encodeURIComponent(campaignId)}/approvals/${stage}`, { method: "POST", body: "{}" });
  revalidatePath(`/campaigns/${campaignId}`);
}
