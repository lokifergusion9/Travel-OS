import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Instagram, CheckCircle2, Send, ExternalLink, ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { assetUrl, listCreatives, listTrips, type Creative, type Trip } from "@/lib/travel";
import {
  connectDev,
  createPost,
  listAccounts,
  listPosts,
  publishNow,
  type Post,
  type SocialAccount,
} from "@/lib/publishing";
import { fadeUp, staggerContainer } from "@/lib/motion";

const statusColor: Record<string, string> = {
  scheduled: "bg-sky-100 text-sky-700",
  publishing: "bg-amber-100 text-amber-700",
  published: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-600",
};

export function Publishing() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [tripId, setTripId] = useState("");
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [picked, setPicked] = useState<Creative | null>(null);
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = () => {
    void listAccounts().then(setAccounts);
    void listPosts().then(setPosts);
  };
  useEffect(() => {
    refresh();
    void listTrips().then(setTrips);
  }, []);

  useEffect(() => {
    setPicked(null);
    if (!tripId) {
      setCreatives([]);
      return;
    }
    void listCreatives(tripId).then((cs) => {
      setCreatives(cs);
      const cap = cs.find((c) => c.kind === "caption");
      if (cap?.text_content) setCaption(cap.text_content);
    });
  }, [tripId]);

  async function connect() {
    setBusy(true);
    try {
      await connectDev("@my_agency");
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    if (!picked) return;
    setBusy(true);
    try {
      const post = await createPost({
        caption,
        image_url: picked.url ?? undefined,
        creative_asset_id: picked.id,
        trip_id: tripId || undefined,
      });
      await publishNow(post.id);
      setPicked(null);
      refresh();
    } finally {
      setBusy(false);
    }
  }

  const posters = creatives.filter((c) => c.kind === "poster");

  return (
    <div>
      <h2 className="mb-6 text-lg font-semibold">Publishing</h2>

      {/* Connection */}
      {accounts.length === 0 ? (
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-black/5 bg-white p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-pink-500 to-orange-400 text-white">
              <Instagram className="h-5 w-5" />
            </div>
            <div>
              <p className="font-medium">Connect Instagram</p>
              <p className="text-sm text-black/50">Use a simulated account to try publishing now.</p>
            </div>
          </div>
          <Button onClick={connect} disabled={busy}>Connect (dev)</Button>
        </div>
      ) : (
        <div className="mb-6 flex items-center gap-3 rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
          <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          <span className="text-sm font-medium text-emerald-800">
            Connected: {accounts[0].account_name} {accounts[0].is_dev && "(dev)"}
          </span>
        </div>
      )}

      {/* Composer */}
      <div className="mb-8 rounded-2xl border border-black/5 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold">New post</h3>
          <select value={tripId} onChange={(e) => setTripId(e.target.value)}
            className="rounded-xl border border-black/10 px-3 py-2 text-sm outline-none">
            <option value="">Pick a trip…</option>
            {trips.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
          </select>
        </div>

        {tripId && posters.length === 0 && (
          <p className="text-sm text-black/40">No posters for this trip yet — generate creatives in its Trip page first.</p>
        )}

        {posters.length > 0 && (
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
            {posters.map((p) => (
              <button key={p.id} onClick={() => setPicked(p)}
                className={`overflow-hidden rounded-xl border-2 transition ${picked?.id === p.id ? "border-[var(--color-ocean-500)]" : "border-transparent"}`}>
                <img src={assetUrl(p.url)} alt="poster" className="aspect-[4/5] w-full object-cover" />
              </button>
            ))}
          </div>
        )}

        {picked && (
          <div className="mt-4 space-y-3">
            <textarea value={caption} onChange={(e) => setCaption(e.target.value)} rows={4}
              placeholder="Write a caption…"
              className="w-full rounded-xl border border-black/10 p-3 text-sm outline-none focus:border-[var(--color-ocean-400)]" />
            <Button onClick={publish} disabled={busy || accounts.length === 0}>
              <Send className="h-4 w-4" /> {busy ? "Publishing…" : "Publish now"}
            </Button>
            {accounts.length === 0 && <span className="ml-3 text-sm text-black/40">Connect an account first.</span>}
          </div>
        )}
      </div>

      {/* Posts */}
      <h3 className="mb-3 font-semibold">Posts</h3>
      {posts.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-black/10 bg-white py-12 text-center text-sm text-black/40">
          Nothing published yet.
        </div>
      ) : (
        <motion.div variants={staggerContainer} initial="initial" animate="animate" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {posts.map((p) => (
            <motion.div key={p.id} variants={fadeUp} className="overflow-hidden rounded-2xl border border-black/5 bg-white">
              {p.image_url ? (
                <img src={assetUrl(p.image_url)} alt="post" className="aspect-square w-full object-cover" />
              ) : (
                <div className="flex aspect-square w-full items-center justify-center bg-black/5"><ImageIcon className="h-8 w-8 text-black/20" /></div>
              )}
              <div className="p-3">
                <div className="mb-1 flex items-center justify-between">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor[p.status]}`}>{p.status}</span>
                  {p.result?.permalink && (
                    <a href={p.result.permalink} target="_blank" rel="noreferrer" className="text-[var(--color-ocean-600)]">
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  )}
                </div>
                <p className="line-clamp-2 text-sm text-black/60">{p.caption}</p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
