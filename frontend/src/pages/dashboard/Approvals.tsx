import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Check, X, CheckCircle2, Map, Sparkles, Mail, Hotel } from "lucide-react";
import { decideApproval, listApprovals, type Approval } from "@/lib/travel";
import { fadeUp, staggerContainer } from "@/lib/motion";

export function Approvals() {
  const [items, setItems] = useState<Approval[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    void listApprovals("pending").then(setItems).catch(() => {});
  }, []);

  async function decide(a: Approval, decision: "approved" | "rejected") {
    setBusy(a.id);
    try {
      await decideApproval(a.id, decision);
      setItems((list) => list.filter((x) => x.id !== a.id));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <h2 className="mb-1 text-lg font-semibold">Approval Center</h2>
      <p className="mb-6 text-sm text-black/50">
        Agents draft, you decide. Nothing goes out without your sign-off.
      </p>

      {items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-black/10 bg-white py-16 text-center">
          <CheckCircle2 className="mx-auto mb-3 h-8 w-8 text-emerald-400" />
          <p className="text-black/50">All caught up — no pending approvals.</p>
        </div>
      ) : (
        <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-3">
          <AnimatePresence>
            {items.map((a) => (
              <motion.div
                key={a.id}
                variants={fadeUp}
                exit={{ opacity: 0, x: 40, transition: { duration: 0.2 } }}
                layout
                className="flex items-center gap-4 rounded-2xl border border-black/5 bg-white p-4"
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--color-ocean-50)]">
                  {a.kind === "itinerary" ? (
                    <Map className="h-5 w-5 text-[var(--color-ocean-600)]" />
                  ) : a.kind === "message" ? (
                    <Mail className="h-5 w-5 text-[var(--color-teal-400)]" />
                  ) : a.kind === "sourcing" ? (
                    <Hotel className="h-5 w-5 text-[var(--color-ocean-500)]" />
                  ) : (
                    <Sparkles className="h-5 w-5 text-[var(--color-sunset-500)]" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-black/5 px-2 py-0.5 text-xs font-medium capitalize text-black/50">
                      {a.kind}
                    </span>
                    <p className="truncate font-medium">{a.title}</p>
                  </div>
                  {a.summary && <p className="mt-0.5 truncate text-sm text-black/50">{a.summary}</p>}
                </div>
                {a.trip_id && (
                  <Link
                    to={`/app/trips/${a.trip_id}`}
                    className="hidden text-sm font-medium text-[var(--color-ocean-600)] hover:underline sm:block"
                  >
                    View
                  </Link>
                )}
                <div className="flex gap-2">
                  <button
                    onClick={() => decide(a, "rejected")}
                    disabled={busy === a.id}
                    className="flex h-9 w-9 items-center justify-center rounded-xl border border-black/10 text-black/50 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                  >
                    <X className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => decide(a, "approved")}
                    disabled={busy === a.id}
                    className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500 text-white transition hover:bg-emerald-600 disabled:opacity-50"
                  >
                    <Check className="h-4 w-4" />
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      )}
    </div>
  );
}
