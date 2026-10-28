import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { TrendingUp, Users, Trophy, Send, Hotel, Megaphone } from "lucide-react";
import { getAnalytics, type Analytics as AnalyticsT } from "@/lib/analytics";
import { STAGE_LABEL, type Stage } from "@/lib/crm";
import { fadeUp, staggerContainer } from "@/lib/motion";

const sourceColor: Record<string, string> = {
  meta: "#1f7aed",
  web: "#8b5cf6",
  whatsapp: "#22c55e",
  instagram: "#ec4899",
  manual: "#94a3b8",
};

export function Analytics() {
  const [data, setData] = useState<AnalyticsT | null>(null);
  useEffect(() => {
    void getAnalytics().then(setData).catch(() => {});
  }, []);

  if (!data) return <div className="py-20 text-center text-black/30">Loading…</div>;
  const { kpis, funnel, by_source } = data;
  const maxFunnel = Math.max(1, ...funnel.map((f) => f.count));
  const totalSource = Math.max(1, by_source.reduce((s, x) => s + x.count, 0));

  const cards = [
    { label: "Total leads", value: kpis.leads_total, icon: Users },
    { label: "Conversion", value: `${kpis.conversion_rate}%`, icon: TrendingUp },
    { label: "Deals won", value: kpis.leads_won, icon: Trophy },
    { label: "Messages sent", value: kpis.messages_sent, icon: Send },
    { label: "Confirmed deals", value: kpis.deals_confirmed, icon: Hotel },
    { label: "Posts published", value: kpis.posts_published, icon: Megaphone },
  ];

  return (
    <div>
      <h2 className="mb-6 text-lg font-semibold">Analytics</h2>

      <motion.div variants={staggerContainer} initial="initial" animate="animate"
        className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        {cards.map((c) => (
          <motion.div key={c.label} variants={fadeUp} className="rounded-2xl border border-black/5 bg-white p-4">
            <c.icon className="mb-2 h-5 w-5 text-[var(--color-ocean-500)]" />
            <p className="text-2xl font-bold">{c.value}</p>
            <p className="text-xs text-black/50">{c.label}</p>
          </motion.div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Funnel */}
        <div className="rounded-2xl border border-black/5 bg-white p-5">
          <h3 className="mb-4 font-semibold">Lead funnel</h3>
          <div className="space-y-3">
            {funnel.map((f, i) => (
              <div key={f.stage}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="text-black/60">{STAGE_LABEL[f.stage as Stage] ?? f.stage}</span>
                  <span className="font-medium">{f.count}</span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-black/5">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(f.count / maxFunnel) * 100}%` }}
                    transition={{ duration: 0.6, delay: i * 0.05, ease: [0.22, 1, 0.36, 1] }}
                    className="h-full rounded-full bg-gradient-to-r from-[var(--color-teal-400)] to-[var(--color-ocean-500)]"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sources */}
        <div className="rounded-2xl border border-black/5 bg-white p-5">
          <h3 className="mb-4 font-semibold">Leads by source</h3>
          {by_source.length === 0 ? (
            <p className="text-sm text-black/40">No leads yet.</p>
          ) : (
            <div className="space-y-3">
              {by_source.map((s, i) => (
                <div key={s.source}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="capitalize text-black/60">{s.source}</span>
                    <span className="font-medium">{s.count}</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-black/5">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(s.count / totalSource) * 100}%` }}
                      transition={{ duration: 0.6, delay: i * 0.05 }}
                      className="h-full rounded-full"
                      style={{ backgroundColor: sourceColor[s.source] ?? "#64748b" }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
