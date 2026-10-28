import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Sparkles,
  Check,
  Loader2,
  ImageIcon,
  FileText,
  MessageSquare,
  Film,
} from "lucide-react";
import { useRef } from "react";
import { Button } from "@/components/ui/Button";
import { streamSSE } from "@/lib/sse";
import {
  approveTrip,
  assetUrl,
  getTrip,
  listCreatives,
  type Creative,
  type TripDetail as TripDetailT,
} from "@/lib/travel";
import { fadeUp, staggerContainer } from "@/lib/motion";

export function TripDetail() {
  const { id = "" } = useParams();
  const [trip, setTrip] = useState<TripDetailT | null>(null);
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [genSteps, setGenSteps] = useState<string[]>([]);
  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);

  const load = () => {
    void getTrip(id).then(setTrip).catch(() => {});
    void listCreatives(id).then(setCreatives).catch(() => {});
  };
  useEffect(load, [id]);

  async function onApprove() {
    setApproving(true);
    try {
      const updated = await approveTrip(id);
      setTrip((t) => (t ? { ...t, status: updated.status } : t));
    } finally {
      setApproving(false);
    }
  }

  async function onGenerate() {
    setGenerating(true);
    setGenSteps([]);
    try {
      await streamSSE(
        `/api/v1/trips/${id}/creatives/generate`,
        { kinds: ["poster", "caption", "brochure", "reel"] },
        (ev) => {
          if (ev.type === "progress") setGenSteps((s) => [...s, String(ev.message)]);
          if (ev.type === "done") {
            void listCreatives(id).then(setCreatives);
            setGenerating(false);
          }
        },
      );
    } catch {
      setGenerating(false);
    }
  }

  if (!trip) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-black/30" />
      </div>
    );
  }

  return (
    <div>
      <Link to="/app/trips" className="mb-4 inline-flex items-center gap-1.5 text-sm text-black/50 hover:text-black">
        <ArrowLeft className="h-4 w-4" /> All trips
      </Link>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{trip.title}</h1>
          {trip.overview && <p className="mt-2 max-w-2xl text-black/60">{trip.overview}</p>}
        </div>
        {trip.status === "pending_review" ? (
          <Button onClick={onApprove} disabled={approving}>
            <Check className="h-4 w-4" /> {approving ? "Approving…" : "Approve itinerary"}
          </Button>
        ) : (
          <span className="rounded-full bg-emerald-100 px-3 py-1.5 text-sm font-medium text-emerald-700">
            ✓ {trip.status}
          </span>
        )}
      </div>

      {/* Itinerary day cards */}
      <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-4">
        {trip.days_plan.map((d) => (
          <motion.div key={d.day_number} variants={fadeUp} className="rounded-2xl border border-black/5 bg-white p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--color-teal-400)] to-[var(--color-ocean-500)] text-sm font-bold text-white">
                {d.day_number}
              </div>
              <h3 className="font-semibold">{d.title}</h3>
            </div>
            {d.summary && <p className="mt-3 text-sm text-black/60">{d.summary}</p>}
            <ul className="mt-3 space-y-1.5">
              {d.activities?.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-black/70">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-ocean-400)]" />
                  {a}
                </li>
              ))}
            </ul>
            {(d.stay || d.transport) && (
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-black/50">
                {d.stay && <span className="rounded-lg bg-black/5 px-2 py-1">🏨 {d.stay}</span>}
                {d.transport && <span className="rounded-lg bg-black/5 px-2 py-1">🚐 {d.transport}</span>}
              </div>
            )}
          </motion.div>
        ))}
      </motion.div>

      {/* Costing */}
      {trip.costing?.per_person != null && (
        <div className="mt-4 rounded-2xl border border-black/5 bg-white p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Estimated price</h3>
            <span className="text-xl font-bold text-[var(--color-ocean-600)]">
              {trip.costing.currency} {trip.costing.per_person.toLocaleString()} / person
            </span>
          </div>
          {trip.costing.breakdown?.length > 0 && (
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {trip.costing.breakdown.map((b, i) => (
                <div key={i} className="rounded-xl bg-black/5 p-3 text-sm">
                  <p className="text-black/50">{b.item}</p>
                  <p className="font-semibold">{trip.costing!.currency} {b.amount?.toLocaleString?.() ?? b.amount}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Creative Studio */}
      <div className="mt-10 mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Creative Studio</h2>
        <Button onClick={onGenerate} disabled={generating} variant="outline" className="border-black/15 text-black hover:bg-black/5">
          <Sparkles className="h-4 w-4 text-[var(--color-sunset-500)]" />
          {generating ? "Generating…" : "Generate creatives"}
        </Button>
      </div>

      {generating && (
        <div className="mb-4 space-y-2 rounded-2xl border border-black/5 bg-white p-4">
          {genSteps.map((s, i) => (
            <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} className="flex items-center gap-2 text-sm text-black/70">
              <Loader2 className="h-4 w-4 animate-spin text-[var(--color-sunset-500)]" /> {s}
            </motion.div>
          ))}
        </div>
      )}

      {creatives.length === 0 && !generating ? (
        <div className="rounded-2xl border border-dashed border-black/10 bg-white py-12 text-center text-black/50">
          No creatives yet. Generate posters, captions and a brochure above.
        </div>
      ) : (
        <motion.div variants={staggerContainer} initial="initial" animate="animate" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {creatives.map((c) => (
            <CreativeCard key={c.id} c={c} />
          ))}
        </motion.div>
      )}
    </div>
  );
}

function CreativeCard({ c }: { c: Creative }) {
  return (
    <motion.div variants={fadeUp} className="overflow-hidden rounded-2xl border border-black/5 bg-white">
      <div className="flex items-center gap-2 border-b border-black/5 px-4 py-3">
        {c.kind === "poster" && <ImageIcon className="h-4 w-4 text-[var(--color-ocean-500)]" />}
        {c.kind === "caption" && <MessageSquare className="h-4 w-4 text-[var(--color-teal-400)]" />}
        {c.kind === "brochure" && <FileText className="h-4 w-4 text-[var(--color-sunset-500)]" />}
        {c.kind === "reel" && <Film className="h-4 w-4 text-pink-500" />}
        <span className="text-sm font-medium capitalize">{c.kind}</span>
        <span className="ml-auto rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">{c.status.replace("_", " ")}</span>
      </div>
      <div className="p-4">
        {c.kind === "poster" && c.url && (
          <img src={assetUrl(c.url)} alt="poster" className="aspect-[4/5] w-full rounded-lg object-cover" />
        )}
        {c.kind === "caption" && (
          <pre className="whitespace-pre-wrap break-words font-sans text-sm text-black/70">{c.text_content}</pre>
        )}
        {c.kind === "brochure" && c.url && (
          <a href={assetUrl(c.url)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-sm font-medium text-[var(--color-ocean-600)] hover:underline">
            <FileText className="h-4 w-4" /> Open brochure PDF
          </a>
        )}
        {c.kind === "reel" && <ReelPreview c={c} />}
      </div>
    </motion.div>
  );
}

interface Scene {
  order: number;
  text: string;
  visual?: string;
  seconds?: number;
}

function ReelPreview({ c }: { c: Creative }) {
  const scenes = (c.meta?.scenes as Scene[] | undefined) ?? [];
  const [i, setI] = useState(0);
  const timer = useRef<number>(0);

  useEffect(() => {
    if (scenes.length === 0) return;
    timer.current = window.setInterval(
      () => setI((p) => (p + 1) % scenes.length),
      2200,
    );
    return () => window.clearInterval(timer.current);
  }, [scenes.length]);

  const scene = scenes[i];
  return (
    <div className="relative mx-auto aspect-[9/16] w-44 overflow-hidden rounded-xl bg-black">
      {c.url && <img src={assetUrl(c.url)} alt="reel" className="absolute inset-0 h-full w-full object-cover opacity-70" />}
      <div className="absolute inset-0 bg-gradient-to-b from-black/10 via-transparent to-black/70" />
      <AnimatePresence mode="wait">
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.4 }}
          className="absolute inset-x-0 bottom-0 p-3 text-center text-sm font-semibold text-white drop-shadow"
        >
          {scene?.text}
        </motion.div>
      </AnimatePresence>
      <div className="absolute left-2 right-2 top-2 flex gap-1">
        {scenes.map((_, idx) => (
          <div key={idx} className={`h-0.5 flex-1 rounded-full ${idx <= i ? "bg-white" : "bg-white/30"}`} />
        ))}
      </div>
    </div>
  );
}
