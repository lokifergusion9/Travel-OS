/** Types + REST calls for trips, creatives, and approvals. */
import { api } from "./api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface Trip {
  id: string;
  title: string;
  destination: string;
  days: number;
  audience: string | null;
  season: string | null;
  budget_per_person: number | null;
  status: string;
  overview: string | null;
  created_at: string;
}

export interface ItineraryDay {
  day_number: number;
  title: string;
  summary: string | null;
  activities: string[];
  stay: string | null;
  transport: string | null;
}

export interface Costing {
  currency: string;
  per_person: number | null;
  breakdown: { item: string; amount: number }[];
}

export interface TripDetail extends Trip {
  days_plan: ItineraryDay[];
  costing: Costing | null;
}

export interface Creative {
  id: string;
  trip_id: string | null;
  kind: "poster" | "caption" | "brochure" | "reel";
  status: string;
  url: string | null;
  text_content: string | null;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface Approval {
  id: string;
  kind: string;
  entity_type: string;
  entity_id: string;
  trip_id: string | null;
  title: string;
  summary: string | null;
  status: string;
  payload: Record<string, unknown>;
  created_at: string;
}

/** Prefix a stored relative URL (/storage/...) with the API origin. */
export function assetUrl(url: string | null): string | undefined {
  if (!url) return undefined;
  return url.startsWith("http") ? url : `${BASE_URL}${url}`;
}

export const listTrips = () => api<Trip[]>("/api/v1/trips");
export const getTrip = (id: string) => api<TripDetail>(`/api/v1/trips/${id}`);
export const approveTrip = (id: string) =>
  api<Trip>(`/api/v1/trips/${id}/approve`, { method: "POST" });
export const listCreatives = (tripId: string) =>
  api<Creative[]>(`/api/v1/trips/${tripId}/creatives`);
export const listApprovals = (status = "pending") =>
  api<Approval[]>(`/api/v1/approvals?status=${status}`);
export const decideApproval = (id: string, decision: "approved" | "rejected") =>
  api<Approval>(`/api/v1/approvals/${id}/decide`, {
    method: "POST",
    body: JSON.stringify({ decision }),
  });
