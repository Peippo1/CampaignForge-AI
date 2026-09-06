import { AppShell } from "@/components/app-shell";
import { CreateBrandKitForm } from "@/components/create-brand-kit-form";
import { BrandKit, listBrandKits } from "@/lib/campaignforge-api";
import { BookOpen } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function BrandKitsPage() {
  let kits: BrandKit[] = [];
  let loadError = "";
  try { kits = await listBrandKits(); } catch (error) { loadError = error instanceof Error ? error.message : "Could not load brand kits."; }
  return <AppShell><div className="page"><header className="page-header"><div><p className="eyebrow">Reusable context</p><h1>Brand kits</h1><p>Give every agent the same verified facts, voice, constraints and approved references.</p></div></header><CreateBrandKitForm />{loadError ? <section className="empty-card service-state"><span><BookOpen /></span><h2>Brand context is temporarily unavailable</h2><p>{loadError}</p></section> : kits.length === 0 ? <section className="empty-card"><span><BookOpen /></span><h2>No brand kits yet</h2><p>Create one above. Agent runs remain deterministic and free in local development.</p></section> : <section className="brand-kit-grid" aria-label="Brand kits">{kits.map((kit) => <article className="content-card" key={kit.brand_kit_id}><div className="card-kicker"><BookOpen /> Brand kit</div><h2>{kit.name}</h2><p>{kit.voice}</p><div className="tag-row"><span>{kit.product_facts.length} facts</span><span>{kit.compliance_rules.length} rules</span><span>{kit.banned_terms.length} banned terms</span></div></article>)}</section>}</div></AppShell>;
}
