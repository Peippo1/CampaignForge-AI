export interface ActionState {
  status: "idle" | "error" | "success";
  message?: string;
  jobId?: string;
}

export const initialActionState: ActionState = { status: "idle" };
