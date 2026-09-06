"use client";

import { useActionState, useState } from "react";
import { createCampaignAction } from "@/app/actions";
import { SubmitButton } from "@/components/submit-button";
import { initialActionState } from "@/lib/action-state";

export function CreateCampaignForm() {
  const [state, action] = useActionState(createCampaignAction, initialActionState);
  const [key] = useState(() => crypto.randomUUID());
  return <form action={action} className="inline-create-form"><input type="hidden" name="idempotency_key" value={key} /><label htmlFor="campaign-title">Campaign name</label><div><input id="campaign-title" name="title" maxLength={120} required placeholder="e.g. Autumn product launch" /><SubmitButton pendingLabel="Creating…">Create campaign</SubmitButton></div>{state.status === "error" && <p className="form-error" role="alert">{state.message}</p>}</form>;
}
