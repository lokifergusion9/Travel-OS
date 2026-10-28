import { useEffect, useState, type DragEvent, type FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Plus, Zap, ZapOff, X, Mail, Phone, Send, Inbox } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth";
import {
  STAGES,
  STAGE_LABEL,
  createLead,
  getLead,
  listLeads,
  replyToLead,
  setAutoFollowup,
  simulateInbound,
  updateStage,
  type Lead,
  type LeadDetail,
  type Stage,
} from "@/lib/crm";

const sourceColor: Record<string, string> = {
  meta: "bg-blue-100 text-blue-700",
  web: "bg-violet-100 text-violet-700",
  instagram: "bg-pink-100 text-pink-700",
  whatsapp: "bg-emerald-100 text-emerald-700",
  manual: "bg-black/5 text-black/50",
};

export function Leads() {
  const { tenant, refreshMe } = useAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [auto, setAuto] = useState(tenant?.auto_followup ?? false);

  const refresh = () => listLeads().then(setLeads).catch(() => {});
  useEffect(() => {
    void refresh();
  }, []);

  async function move(id: string, stage: Stage) {
    setLeads((ls) => ls.map((l) => (l.id === id ? { ...l, stage } : l)));
    await updateStage(id, stage).catch(refresh);
  }

  async function toggleAuto() {
    const next = !auto;
    setAuto(next);
    await setAutoFollowup(next);
    void refreshMe();
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Leads</h2>
        <div className="flex items-center gap-3">
          <button
            onClick={toggleAuto}
            className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition ${
              auto
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-black/10 bg-white text-black/50"
            }`}
          >
            {auto ? <Zap className="h-4 w-4" /> : <ZapOff className="h-4 w-4" />}
            Auto-followup {auto ? "on" : "off"}
          </button>
          <Button onClick={() => setAdding(true)} className="px-4 py-2.5">
            <Plus className="h-4 w-4" /> New lead
          </Button>
        </div>
      </div>

      <AnimatePresence>
        {adding && (
          <NewLeadForm
            onClose={() => setAdding(false)}
            onCreated={() => {
              setAdding(false);
              void refresh();
            }}
          />
        )}
      </AnimatePresence>

      {/* Kanban */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {STAGES.map((stage) => {
          const items = leads.filter((l) => l.stage === stage);
          return (
            <div
              key={stage}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e: DragEvent) => {
                const id = e.dataTransfer.getData("text/lead");
                if (id) void move(id, stage);
              }}
              className="flex w-64 shrink-0 flex-col rounded-2xl bg-black/[0.03] p-3"
            >
              <div className="mb-3 flex items-center justify-between px-1">
                <span className="text-sm font-semibold">{STAGE_LABEL[stage]}</span>
                <span className="rounded-full bg-white px-2 py-0.5 text-xs text-black/50">
                  {items.length}
                </span>
              </div>
              <motion.div layout className="flex flex-col gap-2">
                <AnimatePresence>
                  {items.map((l) => (
                    <motion.div
                      key={l.id}
                      layout
                      initial={{ opacity: 0, scale: 0.97 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0 }}
                      draggable
                      onDragStart={(e) =>
                        (e as unknown as DragEvent).dataTransfer.setData("text/lead", l.id)
                      }
                      onClick={() => setOpenId(l.id)}
                      className="cursor-pointer rounded-xl border border-black/5 bg-white p-3 shadow-sm transition hover:shadow-md"
                    >
                      <div className="flex items-center justify-between">
                        <p className="font-medium">{l.name}</p>
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${sourceColor[l.source] ?? "bg-black/5"}`}>
                          {l.source}
                        </span>
                      </div>
                      <p className="mt-1 truncate text-xs text-black/45">
                        {l.email ?? l.phone ?? "No contact"}
                      </p>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </motion.div>
            </div>
          );
        })}
      </div>

      <AnimatePresence>
        {openId && (
          <LeadDrawer
            id={openId}
            onClose={() => setOpenId(null)}
            onChanged={refresh}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function NewLeadForm({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ name: "", email: "", phone: "" });
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await createLead({ name: form.name, email: form.email || undefined, phone: form.phone || undefined });
      onCreated();
    } finally {
      setBusy(false);
    }
  }
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="mb-4 overflow-hidden"
    >
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3 rounded-2xl border border-black/5 bg-white p-4">
        <Inp label="Name" required value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
        <Inp label="Email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
        <Inp label="Phone" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} />
        <Button type="submit" disabled={busy} className="px-4 py-2.5">
          {busy ? "Adding…" : "Add lead"}
        </Button>
        <button type="button" onClick={onClose} className="p-2 text-black/40 hover:text-black">
          <X className="h-5 w-5" />
        </button>
      </form>
    </motion.div>
  );
}

function LeadDrawer({ id, onClose, onChanged }: { id: string; onClose: () => void; onChanged: () => void }) {
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [reply, setReply] = useState("");
  const [inbound, setInbound] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => {
    void getLead(id).then(setLead).catch(() => {});
  };
  useEffect(load, [id]);

  async function send() {
    if (!reply.trim() || !lead) return;
    setBusy(true);
    try {
      await replyToLead(id, reply, lead.email ? "email" : "whatsapp");
      setReply("");
      await load();
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function fakeInbound() {
    if (!inbound.trim()) return;
    setBusy(true);
    try {
      await simulateInbound(id, inbound, lead?.email ? "email" : "whatsapp");
      setInbound("");
      await load();
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/30"
      />
      <motion.div
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", stiffness: 320, damping: 34 }}
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col bg-white shadow-2xl"
      >
        {!lead ? (
          <div className="flex flex-1 items-center justify-center text-black/30">Loading…</div>
        ) : (
          <>
            <div className="flex items-start justify-between border-b border-black/5 p-5">
              <div>
                <h3 className="text-lg font-bold">{lead.name}</h3>
                <div className="mt-1 flex flex-wrap gap-3 text-sm text-black/50">
                  {lead.email && <span className="flex items-center gap-1"><Mail className="h-3.5 w-3.5" />{lead.email}</span>}
                  {lead.phone && <span className="flex items-center gap-1"><Phone className="h-3.5 w-3.5" />{lead.phone}</span>}
                </div>
                <span className="mt-2 inline-block rounded-full bg-[var(--color-ocean-50)] px-2.5 py-0.5 text-xs font-medium text-[var(--color-ocean-600)]">
                  {STAGE_LABEL[lead.stage]}
                </span>
              </div>
              <button onClick={onClose} className="text-black/40 hover:text-black">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Inbox timeline */}
            <div className="flex-1 space-y-3 overflow-y-auto p-5">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-black/40">
                <Inbox className="h-3.5 w-3.5" /> Conversation
              </div>
              {lead.messages.length === 0 && <p className="text-sm text-black/40">No messages yet.</p>}
              {lead.messages.map((m) => (
                <div key={m.id} className={`flex ${m.direction === "outbound" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm ${
                      m.direction === "outbound"
                        ? "bg-[var(--color-ocean-500)] text-white"
                        : "bg-black/5 text-black/80"
                    }`}
                  >
                    {m.subject && <p className="mb-1 text-xs font-semibold opacity-80">{m.subject}</p>}
                    <p className="whitespace-pre-wrap">{m.body}</p>
                    <p className={`mt-1 text-[10px] ${m.direction === "outbound" ? "text-white/60" : "text-black/40"}`}>
                      {m.channel} · {m.status}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Composer */}
            <div className="space-y-2 border-t border-black/5 p-4">
              <div className="flex gap-2">
                <input
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  placeholder="Type a reply…"
                  className="flex-1 rounded-xl border border-black/10 px-3 py-2.5 text-sm outline-none focus:border-[var(--color-ocean-400)]"
                />
                <Button onClick={send} disabled={busy} className="px-4 py-2.5">
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex gap-2">
                <input
                  value={inbound}
                  onChange={(e) => setInbound(e.target.value)}
                  placeholder="Simulate a lead reply (demo)…"
                  className="flex-1 rounded-xl border border-dashed border-black/15 px-3 py-2 text-xs outline-none"
                />
                <button onClick={fakeInbound} disabled={busy} className="rounded-xl border border-black/10 px-3 text-xs text-black/50 hover:bg-black/5">
                  Receive
                </button>
              </div>
            </div>
          </>
        )}
      </motion.div>
    </>
  );
}

function Inp({ label, value, onChange, required }: { label: string; value: string; onChange: (v: string) => void; required?: boolean }) {
  return (
    <label className="block flex-1">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-black/50">{label}</span>
      <input
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-black/10 px-3 py-2.5 text-sm outline-none focus:border-[var(--color-ocean-400)]"
      />
    </label>
  );
}
