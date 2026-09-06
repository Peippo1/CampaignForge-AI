"use client";

import { Bot, Check, ChevronRight, Circle, MessageSquare, Send, Sparkles, WandSparkles } from "lucide-react";
import { useState } from "react";

const stages = ["Brief", "Strategy", "Copy", "Creative", "Performance", "Activity"];

export function CampaignWorkspace({ campaignId }: { campaignId: string }) {
  const [active, setActive] = useState("Strategy");
  const [message, setMessage] = useState("");
  const [proposal, setProposal] = useState(false);
  const [applied, setApplied] = useState(false);

  function askAgent(event: React.FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;
    setProposal(true);
    setMessage("");
  }

  return (
    <div className="workspace-page">
      <header className="workspace-header">
        <div><p className="breadcrumbs">Campaigns <ChevronRight /> Autumn product launch</p><div className="title-row"><h1>Autumn product launch</h1><span className="badge warning">Strategy review</span></div><p className="campaign-id">Campaign {campaignId} · Updated 12 minutes ago</p></div>
        <div className="header-actions"><button className="button secondary">Share</button><button className="button primary"><Check /> Approve strategy</button></div>
      </header>
      <div className="workspace-layout">
        <nav className="stage-rail" aria-label="Campaign stages">
          {stages.map((stage, index) => <button key={stage} onClick={() => setActive(stage)} className={active === stage ? "stage-active" : ""}><span className={`stage-number ${index < 1 ? "complete" : ""}`}>{index < 1 ? <Check /> : index + 1}</span><span>{stage}</span>{stage === "Strategy" && <small>Review</small>}</button>)}
        </nav>
        <section className="campaign-canvas">
          <div className="canvas-heading"><div><p className="eyebrow">Stage 2 of 6</p><h2>{active}</h2><p>Shape the strategic direction before agents draft channel copy and creative concepts.</p></div><button className="button ghost"><WandSparkles /> Regenerate</button></div>
          <article className="content-card feature-card">
            <div className="card-kicker"><Sparkles /> Campaign direction</div>
            <h3>Make complex campaign operations feel confidently simple.</h3>
            <p>Position CampaignForge as the calm operating layer for small teams: one place to turn a brief into governed, channel-ready work without adding process drag.</p>
            <div className="tag-row"><span>Clarity</span><span>Creative operations</span><span>Small teams</span></div>
          </article>
          <div className="content-columns">
            <article className="content-card"><p className="eyebrow">Primary audience</p><h3>Lean marketing leads</h3><p>Responsible for quality and velocity, but working without dedicated campaign operations support.</p><ul className="check-list"><li><Check /> Needs fast stakeholder alignment</li><li><Check /> Values repeatable systems</li><li><Check /> Avoids unsupported claims</li></ul></article>
            <article className="content-card"><p className="eyebrow">Recommended channels</p><h3>Focused distribution</h3><div className="channel-row"><span>in</span><div><strong>LinkedIn</strong><small>Thought leadership + proof</small></div></div><div className="channel-row"><span>@</span><div><strong>Email</strong><small>Nurture + launch sequence</small></div></div></article>
          </div>
          <article className="content-card"><div className="panel-heading"><div><p className="eyebrow">Risks and guardrails</p><h3>Keep the campaign credible</h3></div><span className="badge neutral">3 checks</span></div><div className="risk-row"><Circle /> Do not promise guaranteed performance or time savings.</div><div className="risk-row"><Circle /> Keep approval language explicit before paid generation.</div><div className="risk-row"><Circle /> Attribute media metrics to their source platform.</div></article>
        </section>
        <aside className="agent-panel">
          <div className="agent-heading"><span className="agent-avatar"><Bot /></span><div><strong>Campaign agent</strong><small><span className="online-dot" /> Ready</small></div><button aria-label="Open conversation options" className="icon-button"><MessageSquare /></button></div>
          <div className="conversation" aria-live="polite">
            <div className="agent-message"><strong>Strategy is ready for review.</strong><p>I built this direction from your brief and brand kit. I can sharpen the audience, compare angles, or explain any recommendation.</p></div>
            <div className="prompt-chips"><button onClick={() => setMessage("Give me a bolder alternative")}>Make it bolder</button><button onClick={() => setMessage("Explain the channel choice")}>Explain channels</button></div>
            {proposal && <div className="proposal-card"><div className="card-kicker"><Sparkles /> Proposed revision</div><strong>Sharper strategic line</strong><p>Campaign operations that move at the speed of your best ideas—without losing control.</p>{applied ? <span className="applied"><Check /> Applied as revision 2</span> : <div className="proposal-actions"><button className="button secondary" onClick={() => setProposal(false)}>Dismiss</button><button className="button primary" onClick={() => setApplied(true)}>Apply revision</button></div>}</div>}
          </div>
          <form className="agent-compose" onSubmit={askAgent}><label htmlFor="agent-message">Ask about this campaign</label><div><textarea id="agent-message" value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Ask for a variation or explanation…" rows={2} /><button className="send-button" aria-label="Send message"><Send /></button></div><small>Agent changes require your explicit approval.</small></form>
        </aside>
      </div>
      <button className="mobile-agent-button"><Bot /> Ask agent</button>
    </div>
  );
}
