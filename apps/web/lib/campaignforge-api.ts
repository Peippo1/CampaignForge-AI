import { cookies } from "next/headers";

export type CampaignStage =
  | "draft"
  | "strategy_ready"
  | "strategy_approved"
  | "copy_ready"
  | "copy_approved"
  | "image_generation_approved"
  | "assets_ready"
  | "final_approved";

export interface CampaignRevision {
  revision: number;
  stage: CampaignStage;
  actor_user_id: string;
  created_at: string;
  source: string;
  model: string | null;
  prompt_version: string | null;
  run_id: string | null;
}

export interface Campaign {
  campaign_id: string;
  workspace_id: string;
  title: string;
  created_by: string;
  stage: CampaignStage;
  revision: number;
  strategy: Record<string, unknown> | null;
  copy: Record<string, unknown> | null;
  approvals: Array<{ stage: CampaignStage; actor_user_id: string; created_at: string }>;
  image_authorization: { count: number; estimated_cost_minor: number } | null;
  assets: Array<{ asset_id: string; approval_status: string; review_reason: string | null }>;
  revisions: CampaignRevision[];
  export_enabled: boolean;
}

export interface BrandKit {
  brand_kit_id: string;
  workspace_id: string;
  name: string;
  voice: string;
  audiences: string[];
  product_facts: string[];
  required_phrases: string[];
  banned_terms: string[];
  compliance_rules: string[];
}

export interface AgentJob {
  job_id: string;
  workspace_id: string;
  kind: string;
  status: "queued" | "running" | "succeeded" | "failed";
  created_at: string;
  payload: Record<string, unknown>;
}

export class CampaignForgeApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
    public readonly retryable = false,
  ) {
    super(message);
    this.name = "CampaignForgeApiError";
  }
}

const API_URL = (process.env.CAMPAIGNFORGE_API_URL || process.env.NEXT_PUBLIC_CAMPAIGNFORGE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const WORKSPACE_ID = process.env.CAMPAIGNFORGE_WORKSPACE_ID || "local-demo";

async function requestHeaders(idempotencyKey?: string): Promise<HeadersInit> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-CampaignForge-Workspace": WORKSPACE_ID,
  };
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  const session = (await cookies()).get("campaignforge_session")?.value;
  if (session) {
    headers.Authorization = `Bearer ${session}`;
    headers["X-CampaignForge-Token-Type"] = "session-cookie";
  } else if (process.env.NODE_ENV !== "production" || process.env.CAMPAIGNFORGE_WEB_AUTH_MODE === "development") {
    headers["X-CampaignForge-User"] = process.env.CAMPAIGNFORGE_DEV_USER_ID || "local-owner";
    headers["X-CampaignForge-Role"] = process.env.CAMPAIGNFORGE_DEV_ROLE || "owner";
  } else {
    throw new CampaignForgeApiError("Sign in to continue.", 401, "authentication_required");
  }
  return headers;
}

export async function campaignForgeFetch<T>(
  path: string,
  init: RequestInit & { idempotencyKey?: string } = {},
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...(await requestHeaders(init.idempotencyKey)), ...init.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const error = payload?.error;
    throw new CampaignForgeApiError(
      error?.message || payload?.detail || "CampaignForge could not complete the request.",
      response.status,
      error?.code || "request_failed",
      Boolean(error?.retryable),
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const listCampaigns = () => campaignForgeFetch<Campaign[]>("/v1/campaigns");
export const getCampaign = (campaignId: string) => campaignForgeFetch<Campaign>(`/v1/campaigns/${encodeURIComponent(campaignId)}`);
export const listBrandKits = () => campaignForgeFetch<BrandKit[]>("/v1/brand-kits");
export const getJob = (jobId: string) => campaignForgeFetch<AgentJob>(`/v1/jobs/${encodeURIComponent(jobId)}`);
