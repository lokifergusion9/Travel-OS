/** Types + REST calls for sourcing (vendors, deals). */
import { api } from "./api";

export const VENDOR_TYPES = ["hotel", "transport", "activity"] as const;
export type VendorType = (typeof VENDOR_TYPES)[number];
export const DEAL_STATUSES = ["requested", "negotiating", "confirmed", "declined"] as const;
export type DealStatus = (typeof DEAL_STATUSES)[number];

export interface Vendor {
  id: string;
  name: string;
  type: VendorType;
  location: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  notes: string | null;
}

export interface Deal {
  id: string;
  trip_id: string | null;
  vendor_id: string;
  kind: string;
  status: DealStatus;
  outreach_subject: string | null;
  outreach_body: string | null;
  sent: boolean;
  terms: string | null;
  amount: number | null;
  currency: string;
  created_at: string;
}

export const listVendors = () => api<Vendor[]>("/api/v1/vendors");
export const createVendor = (data: Partial<Vendor> & { name: string; type: VendorType }) =>
  api<Vendor>("/api/v1/vendors", { method: "POST", body: JSON.stringify(data) });
export const deleteVendor = (id: string) =>
  api<void>(`/api/v1/vendors/${id}`, { method: "DELETE" });
export const generateSourcing = (tripId: string) =>
  api<{ deals_created: number }>(`/api/v1/trips/${tripId}/sourcing/generate`, { method: "POST" });
export const listDeals = (tripId?: string) =>
  api<Deal[]>(`/api/v1/deals${tripId ? `?trip_id=${tripId}` : ""}`);
export const updateDeal = (id: string, data: { status?: DealStatus; terms?: string; amount?: number }) =>
  api<Deal>(`/api/v1/deals/${id}`, { method: "PATCH", body: JSON.stringify(data) });
