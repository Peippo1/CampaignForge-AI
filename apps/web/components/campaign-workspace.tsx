"use client";

import { approveCampaignStageAction, runAgentAction } from "@/app/actions";
import { SubmitButton } from "@/components/submit-button";
import { initialActionState } from "@/lib/action-state";
import type { Campaign } from "@/lib/campaignforge-api";
import { Bot, Check, ChevronRight, Circle, Clock3, Sparkles, WandSparkles } from "lucide-react";
import Link from "next/link";
import { useActionState, useEffect, useState } from "react";

const stages = ["Brief", "Strategy", "Copy", "Creative", "Performance", "Activity"];
const stageIndex: Record<string, number> = { draft: 0, strategy_ready: 1, strategy_approved: 2, copy_ready: 2, copy_approved: 3, image_generation_approved: 3, assets_ready: 3, final_approved: 5 };
const stageLabels: Record<string, string> = { draft: "Brief needed", strategy_ready: "Strategy review", strategy_approved: "Strategy approved", copy_ready: "Copy review", copy_approved: "Copy approved", image_generation_approved: "Images authorized", assets_ready: "Asset review", final_approved: "Final approved" };

function stringList(value: unknown): string[] { return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []; }

export function CampaignWorkspace({ campaign }: { campaign: Campaign }) {
  const currentIndex = stageIndex[campaign.stage] ?? 0;
  const [active, setActive] = useState(stages[currentIndex]);
  const [key] = useState(() => crypto.randomUUID());
  const [runState, runAction] = useActionState(runAgentAction.bind(null, campaign.campaign_id), initialActionState);
  const [jobStatus, setJobStatus] = useState<string>();

  useEffect(() => {
    if (!runState.jobId) return;
    let activePoll = true;
    const poll = async (attempt = 0) => {
      const response = await fetch(`/api/jobs/${runState.jobId}`, { cache: "no-store" });
      if (!response.ok || !activePoll) return;
      const job = await response.json();
      setJobStatus(job.status);
      if (["queued", "running"].includes(job.status) && attempt < 20) window.setTimeout(() => void poll(attempt + 1), 1800);
      if (["queued", "running"].includes(job.status) && attempt >= 20) setJobStatus("delayed — refresh to check again");
      if (job.status === "succeeded") window.location.reload();
    };
    void poll();
    return () => { activePoll = false; };
  }, [runState.jobId]);

  const strategy = campaign.strategy || {};
  const copy = campaign.copy || {};
  const canApprove = campaign.stage === "strategy_ready" || campaign.stage === "copy_ready" || campaign.stage === "assets_ready";
  const approvalStage = campaign.stage === "strategy_ready" ? "strategy" : campaign.stage === "copy_ready" ? "copy" : "final";

  return <div className="workspace-page"><header className="workspace-header"><div><p className="breadcrumbs"><Link href="/campaigns">Campaigns</Link><ChevronRight />{campaign.title}</p><div className="title-row"><h1>{campaign.title}</h1><span className={`badge ${canApprove ? "warning" : campaign.export_enabled ? "success" : "neutral"}`}>{stageLabels[campaign.stage]}</span></div><p className="campaign-id">Campaign {campaign.campaign_id.slice(0, 8)} · Revision {campaign.revision}</p></div><div className="header-actions"><Link href="/campaigns" className="button secondary">All campaigns</Link>{canApprove && <form action={approveCampaignStageAction.bind(null, campaign.campaign_id, approvalStage)}><SubmitButton pendingLabel="Approving…"><Check /> Approve {approvalStage}</SubmitButton></form>}</div></header><div className="workspace-layout"><nav className="stage-rail" aria-label="Campaign stages">{stages.map((stage, index) => <button key={stage} onClick={() => setActive(stage)} className={active === stage ? "stage-active" : ""}><span className={`stage-number ${index < currentIndex ? "complete" : ""}`}>{index < currentIndex ? <Check /> : index + 1}</span><span>{stage}</span>{index === currentIndex && <small>Current</small>}</button>)}</nav><section className="campaign-canvas"><div className="canvas-heading"><div><p className="eyebrow">Stage {currentIndex + 1} of 6</p><h2>{active}</h2><p>Every generated change moves through the same revision and approval controls.</p></div></div><CampaignContent active={active} campaign={campaign} strategy={strategy} copy={copy} /></section><aside className="agent-panel"><div className="agent-heading"><span className="agent-avatar"><Bot /></span><div><strong>Campaign agent</strong><small><span className="online-dot" /> Low-cost mode</small></div></div><div className="conversation" aria-live="polite"><div className="agent-message"><strong>{campaign.stage === "draft" ? "Ready to shape your brief." : "Campaign state loaded."}</strong><p>Local development uses deterministic mock output. Production model calls remain behind explicit configuration and approval gates.</p></div>{runState.message && <div className={`run-notice ${runState.status}`} role="status"><Clock3 /> <span>{runState.message}{jobStatus ? ` Status: ${jobStatus}.` : ""}</span></div>}</div><form className="agent-compose" action={runAction}><input type="hidden" name="idempotency_key" value={key} /><input type="hidden" name="kind" value={campaign.stage === "strategy_approved" ? "copy" : "strategy"} /><label htmlFor="agent-instructions">{campaign.stage === "strategy_approved" ? "Copy instructions" : "Campaign brief"}</label><div><textarea id="agent-instructions" name="instructions" placeholder="Describe the audience, offer, desired outcome and constraints…" minLength={20} maxLength={4000} required rows={5} /></div><SubmitButton className="button primary agent-submit" pendingLabel="Queuing…"><WandSparkles /> Generate {campaign.stage === "strategy_approved" ? "copy" : "strategy"}</SubmitButton><small>Submitting queues a job; it never approves or publishes work.</small></form></aside></div><button className="mobile-agent-button"><Bot /> Ask agent</button></div>;
}

function CampaignContent({ active, campaign, strategy, copy }: { active: string; campaign: Campaign; strategy: Record<string, unknown>; copy: Record<string, unknown> }) {
  if (active === "Strategy") return strategy.summary ? <><article className="content-card feature-card"><div className="card-kicker"><Sparkles /> Campaign direction</div><h3>{String(strategy.summary)}</h3><div className="tag-row">{stringList(strategy.objectives).map((item) => <span key={item}>{item}</span>)}</div></article><div className="content-columns"><ListCard title="Audiences" items={stringList(strategy.audiences)} /><ListCard title="Channels" items={stringList(strategy.channels)} /></div><ListCard title="Risks and guardrails" items={stringList(strategy.risks)} /></> : <EmptyStage title="No strategy draft yet" description="Use the campaign agent to turn the brief into a structured strategy." />;
  if (active === "Copy") return Object.keys(copy).length ? <><ListCard title="Headlines" items={stringList(copy.headlines)} /><ListCard title="Body copy" items={stringList(copy.body_copy)} /><ListCard title="Calls to action" items={stringList(copy.calls_to_action)} /></> : <EmptyStage title="Copy waits for approved strategy" description="Approve strategy before asking the copywriter specialist for channel-ready drafts." />;
  if (active === "Creative") return <EmptyStage title={campaign.assets.length ? `${campaign.assets.length} assets ready for review` : "Creative generation is gated"} description="Copy approval and an explicit image-count/cost confirmation are required before paid generation." />;
  if (active === "Activity") return <article className="content-card"><p className="eyebrow">Immutable revisions</p><h3>{campaign.revisions.length} recorded changes</h3>{campaign.revisions.map((revision) => <div className="activity-row" key={revision.revision}><span>v{revision.revision}</span><div><strong>{stageLabels[revision.stage]}</strong><small>{revision.source} · {revision.model || "manual"}</small></div></div>)}</article>;
  return <EmptyStage title={`${active} workspace`} description={active === "Brief" ? "Your campaign name is saved. Add the detailed brief in the agent panel to begin." : "This view will populate as connected platform data and approvals become available."} />;
}

function ListCard({ title, items }: { title: string; items: string[] }) { return <article className="content-card"><p className="eyebrow">{title}</p>{items.length ? <ul className="check-list">{items.map((item) => <li key={item}><Circle />{item}</li>)}</ul> : <p>No items yet.</p>}</article>; }
function EmptyStage({ title, description }: { title: string; description: string }) { return <article className="empty-card canvas-empty"><span><Sparkles /></span><h3>{title}</h3><p>{description}</p></article>; }
