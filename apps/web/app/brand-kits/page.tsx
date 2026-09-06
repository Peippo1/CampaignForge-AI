import { AppShell } from "@/components/app-shell";
import { BookOpen, Plus } from "lucide-react";

export default function BrandKitsPage() { return <AppShell><div className="page"><header className="page-header"><div><p className="eyebrow">Reusable context</p><h1>Brand kits</h1><p>Give every agent the same facts, voice, constraints, and approved references.</p></div><button className="button primary"><Plus/> New brand kit</button></header><section className="empty-card"><span><BookOpen/></span><h2>CampaignForge core brand</h2><p>Clear, credible and useful · 6 product facts · 3 compliance rules · 4 references</p><button className="button secondary">Open brand kit</button></section></div></AppShell>; }
