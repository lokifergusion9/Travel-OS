/** Analytics overview types + call. */
import { api } from "./api";

export interface Analytics {
  kpis: {
    leads_total: number;
    leads_won: number;
    conversion_rate: number;
    trips_total: number;
    trips_approved: number;
    creatives_total: number;
    deals_total: number;
    deals_confirmed: number;
    posts_published: number;
    messages_sent: number;
    messages_received: number;
  };
  funnel: { stage: string; count: number }[];
  by_source: { source: string; count: number }[];
}

export const getAnalytics = () => api<Analytics>("/api/v1/analytics/overview");
