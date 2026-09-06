"use client";

import { useActionState } from "react";
import { createBrandKitAction } from "@/app/actions";
import { SubmitButton } from "@/components/submit-button";
import { initialActionState } from "@/lib/action-state";

export function CreateBrandKitForm() {
  const [state, action] = useActionState(createBrandKitAction, initialActionState);
  return <form action={action} className="brand-kit-form panel"><div className="panel-heading"><div><p className="eyebrow">Shared agent context</p><h2>Create a brand kit</h2></div></div><div className="form-grid"><label>Name<input name="name" required maxLength={160} placeholder="CampaignForge core" /></label><label>Voice<input name="voice" required maxLength={4000} placeholder="Clear, credible and useful" /></label><label>Audiences<textarea name="audiences" rows={3} placeholder="Small marketing teams, agencies" /></label><label>Product facts<textarea name="product_facts" rows={3} placeholder="One verified fact per line" /></label><label>Required phrases<textarea name="required_phrases" rows={3} /></label><label>Banned terms<textarea name="banned_terms" rows={3} /></label><label className="form-wide">Compliance rules<textarea name="compliance_rules" rows={3} placeholder="Never make unsupported performance claims" /></label></div><div className="form-footer"><span>{state.message && <span className={state.status === "error" ? "form-error" : "form-success"} role="status">{state.message}</span>}</span><SubmitButton pendingLabel="Saving…">Save brand kit</SubmitButton></div></form>;
}
