import { useEffect, useState, type FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import { Map, Plus, Sparkles, Loader2, ArrowRight, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { streamSSE } from "@/lib/sse";
import { listTrips, type Trip } from "@/lib/travel";
import { fadeUp, staggerContainer } from "@/lib/motion";

const statusColor: Record<string, string> = {
  pending_review: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
  generating: "bg-sky-100 text-sky-700",
  draft: "bg-black/5 text-black/50",
};

export function Trips() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [building, setBuilding] = useState(false);

  const refresh = () => listTrips().then(setTrips).catch(() => {});
  useEffect(() => {
    void refresh();
  }, []);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Trips</h2>
        <Button onClick={() => setBuilding(true)} className="px-4 py-2.5">
          <Plus className="h-4 w-4" /> New trip
        </Button>
      </div>

      <AnimatePresence>
        {building && <TripBuilder onClose={() => setBuilding(false)} />}
      </AnimatePresence>

      {trips.length === 0 ? (
        <div className="mt-10 rounded-2xl border border-dashed border-black/10 bg-white py-16 text-center">
          <Map className="mx-auto mb-3 h-8 w-8 text-black/20" />
          <p className="text-black/50">No trips yet. Build your first one above.</p>
        </div>
      ) : (
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {trips.map((t) => (
            <motion.div key={t.id} variants={fadeUp} whileHover={{ y: -4 }}>
              <Link
                to={`/app/trips/${t.id}`}
                className="group block rounded-2xl border border-black/5 bg-white p-5 transition hover:shadow-lg hover:shadow-black/5"
              >
                <div className="mb-3 flex items-center justify-between">
                  <span className="rounded-lg bg-[var(--color-ocean-50)] px-2 py-1 text-xs font-medium text-[var(--color-ocean-600)]">
                    {t.destination}
                  </span>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusColor[t.status] ?? "bg-black/5"}`}>
                    {t.status.replace("_", " ")}
                  </span>
                </div>
                <h3 className="font-semibold">{t.title}</h3>
                <p className="mt-1 text-sm text-black/50">{t.days} days</p>
                <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[var(--color-ocean-600)]">
                  Open <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
                </span>
              </Link>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}

function TripBuilder({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({ destination: "", days: 4, audience: "", budget_per_person: "" });
  const [steps, setSteps] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const upd = (k: string) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSteps([]);
    try {
      await streamSSE(
        "/api/v1/trips/generate",
        {
          destination: form.destination,
          days: Number(form.days),
          audience: form.audience || null,
          budget_per_person: form.budget_per_person ? Number(form.budget_per_person) : null,
        },
        (ev) => {
          if (ev.type === "progress") setSteps((s) => [...s, String(ev.message)]);
          if (ev.type === "trip") navigate(`/app/trips/${ev.trip_id}`);
        },
      );
    } catch {
      setBusy(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="mb-6 overflow-hidden"
    >
      <div className="rounded-2xl border border-black/5 bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold">New trip</h3>
          <button onClick={onClose} className="text-black/40 hover:text-black">
            <X className="h-5 w-5" />
          </button>
        </div>
        {!busy ? (
          <form onSubmit={onSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input label="Destination" required value={form.destination} onChange={upd("destination")} placeholder="Spiti Valley" />
            <Input label="Days" type="number" min={1} max={30} value={form.days} onChange={upd("days")} />
            <Input label="Audience" value={form.audience} onChange={upd("audience")} placeholder="College groups" />
            <Input label="Budget / person (₹)" type="number" value={form.budget_per_person} onChange={upd("budget_per_person")} placeholder="12000" />
            <div className="sm:col-span-2">
              <Button type="submit" className="w-full">
                <Sparkles className="h-4 w-4" /> Generate itinerary
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-3 py-2">
            {steps.map((s, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-3 text-sm text-black/70"
              >
                <Loader2 className="h-4 w-4 animate-spin text-[var(--color-ocean-500)]" />
                {s}
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

function Input({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-black/50">
        {label}
      </span>
      <input
        {...props}
        className="w-full rounded-xl border border-black/10 bg-white px-4 py-3 outline-none transition focus:border-[var(--color-ocean-400)] focus:ring-2 focus:ring-[var(--color-ocean-400)]/30"
      />
    </label>
  );
}
