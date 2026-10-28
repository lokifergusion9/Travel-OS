import { useEffect, useState, type FormEvent } from "react";
import { motion } from "framer-motion";
import { Hotel, Bus, Plus, Trash2, Sparkles, Send } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { listTrips, type Trip } from "@/lib/travel";
import {
  VENDOR_TYPES,
  DEAL_STATUSES,
  createVendor,
  deleteVendor,
  generateSourcing,
  listDeals,
  listVendors,
  updateDeal,
  type Deal,
  type DealStatus,
  type Vendor,
  type VendorType,
} from "@/lib/sourcing";
import { fadeUp, staggerContainer } from "@/lib/motion";

const dealColor: Record<DealStatus, string> = {
  requested: "bg-sky-100 text-sky-700",
  negotiating: "bg-amber-100 text-amber-700",
  confirmed: "bg-emerald-100 text-emerald-700",
  declined: "bg-red-100 text-red-600",
};

export function Sourcing() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [tripId, setTripId] = useState("");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");

  const vendorName = (id: string) => vendors.find((v) => v.id === id)?.name ?? "Vendor";
  const refresh = () => {
    void listVendors().then(setVendors);
    void listDeals(tripId || undefined).then(setDeals);
  };
  useEffect(() => {
    void listTrips().then(setTrips);
  }, []);
  useEffect(refresh, [tripId]);

  async function generate() {
    if (!tripId) {
      setNote("Pick a trip first.");
      return;
    }
    setBusy(true);
    setNote("");
    try {
      const r = await generateSourcing(tripId);
      setNote(`Drafted ${r.deals_created} outreach email(s) — approve them in the Approval Center.`);
      void listDeals(tripId).then(setDeals);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Sourcing</h2>
        <div className="flex items-center gap-2">
          <select
            value={tripId}
            onChange={(e) => setTripId(e.target.value)}
            className="rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm outline-none"
          >
            <option value="">All trips</option>
            {trips.map((t) => (
              <option key={t.id} value={t.id}>{t.title}</option>
            ))}
          </select>
          <Button onClick={generate} disabled={busy} className="px-4 py-2.5">
            <Sparkles className="h-4 w-4" /> {busy ? "Drafting…" : "Generate outreach"}
          </Button>
        </div>
      </div>
      {note && <p className="mb-4 rounded-xl bg-[var(--color-ocean-50)] px-4 py-2 text-sm text-[var(--color-ocean-700)]">{note}</p>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Vendors */}
        <div className="lg:col-span-2">
          <h3 className="mb-3 font-semibold">Vendors</h3>
          <VendorForm onCreated={refresh} />
          <motion.div variants={staggerContainer} initial="initial" animate="animate" className="mt-3 space-y-2">
            {vendors.map((v) => (
              <motion.div key={v.id} variants={fadeUp} className="flex items-center gap-3 rounded-xl border border-black/5 bg-white p-3">
                {v.type === "transport" ? <Bus className="h-4 w-4 text-[var(--color-ocean-500)]" /> : <Hotel className="h-4 w-4 text-[var(--color-sunset-500)]" />}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{v.name}</p>
                  <p className="truncate text-xs text-black/45">{v.contact_email ?? v.type}</p>
                </div>
                <button onClick={() => deleteVendor(v.id).then(refresh)} className="text-black/30 hover:text-red-600">
                  <Trash2 className="h-4 w-4" />
                </button>
              </motion.div>
            ))}
            {vendors.length === 0 && <p className="text-sm text-black/40">No vendors yet — add hotels & transport partners.</p>}
          </motion.div>
        </div>

        {/* Deals */}
        <div className="lg:col-span-3">
          <h3 className="mb-3 font-semibold">Deals</h3>
          {deals.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-black/10 bg-white py-12 text-center text-sm text-black/40">
              No deals yet. Add vendors, pick a trip, and generate outreach.
            </div>
          ) : (
            <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-3">
              {deals.map((d) => (
                <motion.div key={d.id} variants={fadeUp} className="rounded-2xl border border-black/5 bg-white p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{vendorName(d.vendor_id)}</span>
                      <span className="rounded-full bg-black/5 px-2 py-0.5 text-xs capitalize text-black/50">{d.kind}</span>
                      {d.sent && <span className="flex items-center gap-1 text-xs text-emerald-600"><Send className="h-3 w-3" /> sent</span>}
                    </div>
                    <select
                      value={d.status}
                      onChange={(e) => updateDeal(d.id, { status: e.target.value as DealStatus }).then(refresh)}
                      className={`rounded-full px-2.5 py-1 text-xs font-medium ${dealColor[d.status]}`}
                    >
                      {DEAL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  {d.outreach_body && <p className="mt-2 line-clamp-2 text-sm text-black/55">{d.outreach_body}</p>}
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}

function VendorForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState<{ name: string; type: VendorType; contact_email: string }>({
    name: "",
    type: "hotel",
    contact_email: "",
  });
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await createVendor({ name: form.name, type: form.type, contact_email: form.contact_email || undefined });
      setForm({ name: "", type: "hotel", contact_email: "" });
      onCreated();
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="space-y-2 rounded-2xl border border-black/5 bg-white p-3">
      <input required placeholder="Vendor name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
        className="w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-[var(--color-ocean-400)]" />
      <div className="flex gap-2">
        <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value as VendorType })}
          className="rounded-lg border border-black/10 px-2 py-2 text-sm capitalize outline-none">
          {VENDOR_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <input placeholder="Email" value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
          className="flex-1 rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-[var(--color-ocean-400)]" />
        <Button type="submit" disabled={busy} className="px-3 py-2"><Plus className="h-4 w-4" /></Button>
      </div>
    </form>
  );
}
