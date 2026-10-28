/** Types + REST calls for the CRM (leads, messages, pipeline). */
import { api } from "./api";

export const STAGES = [
  "new",
  "contacted",
  "interested",
  "proposal",
  "negotiation",
  "won",
  "lost",
] as const;
export type Stage = (typeof STAGES)[number];

export const STAGE_LABEL: Record<Stage, string> = {
  new: "New",
  contacted: "Contacted",
  interested: "Interested",
  proposal: "Proposal",
  negotiation: "Negotiation",
  won: "Won",
  lost: "Lost",
};

export interface Lead {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  source: string;
  stage: Stage;
  score: number;
  trip_id: string | null;
  notes: string | null;
  last_contacted_at: string | null;
  created_at: string;
}

export interface LeadMessage {
  id: string;
  channel: string;
  direction: "outbound" | "inbound";
  subject: string | null;
  body: string;
  status: string;
  created_at: string;
}

export interface LeadActivity {
  id: string;
  type: string;
  content: string | null;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface LeadDetail extends Lead {
  messages: LeadMessage[];
  activities: LeadActivity[];
}

export const listLeads = () => api<Lead[]>("/api/v1/leads");
export const createLead = (data: { name: string; email?: string; phone?: string }) =>
  api<Lead>("/api/v1/leads", { method: "POST", body: JSON.stringify(data) });
export const getLead = (id: string) => api<LeadDetail>(`/api/v1/leads/${id}`);
export const updateStage = (id: string, stage: Stage) =>
  api<Lead>(`/api/v1/leads/${id}/stage`, {
    method: "PATCH",
    body: JSON.stringify({ stage }),
  });
export const replyToLead = (id: string, body: string, channel = "email") =>
  api<LeadMessage>(`/api/v1/leads/${id}/reply`, {
    method: "POST",
    body: JSON.stringify({ body, channel }),
  });
export const simulateInbound = (id: string, body: string, channel = "email") =>
  api<Lead>(`/api/v1/leads/${id}/inbound`, {
    method: "POST",
    body: JSON.stringify({ body, channel }),
  });
export const setAutoFollowup = (enabled: boolean) =>
  api<{ auto_followup: boolean }>(
    `/api/v1/settings/auto-followup?enabled=${enabled}`,
    { method: "POST" },
  );
