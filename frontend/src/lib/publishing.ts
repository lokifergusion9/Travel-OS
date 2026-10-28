/** Types + REST calls for publishing (Instagram). */
import { api } from "./api";

export interface SocialAccount {
  id: string;
  platform: string;
  account_name: string;
  ig_user_id: string | null;
  connected: boolean;
  is_dev: boolean;
}

export interface Post {
  id: string;
  social_account_id: string | null;
  trip_id: string | null;
  image_url: string | null;
  caption: string | null;
  status: "scheduled" | "publishing" | "published" | "failed";
  scheduled_at: string | null;
  published_at: string | null;
  result: { permalink?: string; mock?: boolean; detail?: string };
  created_at: string;
}

export const listAccounts = () => api<SocialAccount[]>("/api/v1/publishing/accounts");
export const connectDev = (account_name: string) =>
  api<SocialAccount>("/api/v1/publishing/connect/dev", {
    method: "POST",
    body: JSON.stringify({ account_name }),
  });
export const listPosts = () => api<Post[]>("/api/v1/publishing/posts");
export const createPost = (data: {
  caption: string;
  image_url?: string;
  creative_asset_id?: string;
  trip_id?: string;
}) => api<Post>("/api/v1/publishing/posts", { method: "POST", body: JSON.stringify(data) });
export const publishNow = (id: string) =>
  api<Post>(`/api/v1/publishing/posts/${id}/publish`, { method: "POST" });
