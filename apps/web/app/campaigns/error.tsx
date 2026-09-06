"use client";

import { AlertTriangle } from "lucide-react";

export default function CampaignsError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <div className="page"><section className="empty-card service-state"><span><AlertTriangle /></span><h1>Campaign workspace unavailable</h1><p>The API may still be starting, or your session may have expired.</p><button className="button primary" onClick={reset}>Try again</button></section></div>;
}
