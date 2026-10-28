import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Map, CheckCircle2, Sparkles, ArrowRight } from "lucide-react";
import { listTrips, listApprovals } from "@/lib/travel";
import { fadeUp, staggerContainer } from "@/lib/motion";

export function Overview() {
  const [trips, setTrips] = useState(0);
  const [approved, setApproved] = useState(0);
  const [pending, setPending] = useState(0);

  useEffect(() => {
    void (async () => {
      const [t, p] = await Promise.all([listTrips(), listApprovals("pending")]);
      setTrips(t.length);
      setApproved(t.filter((x) => x.status === "approved").length);
      setPending(p.length);
    })().catch(() => {});
  }, []);

  const stats = [
    { label: "Total trips", value: trips },
    { label: "Approved", value: approved },
    { label: "Pending approvals", value: pending },
    { label: "Deals closed", value: 0 },
  ];

  return (
    <div>
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="mb-10 grid grid-cols-2 gap-4 lg:grid-cols-4"
      >
        {stats.map((s) => (
          <motion.div
            key={s.label}
            variants={fadeUp}
            className="rounded-2xl border border-black/5 bg-white p-5"
          >
            <p className="text-sm text-black/50">{s.label}</p>
            <p className="mt-1 text-3xl font-bold">{s.value}</p>
          </motion.div>
        ))}
      </motion.div>

      <h2 className="mb-4 text-lg font-semibold">Jump in</h2>
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
      >
        <ActionCard
          to="/app/trips"
          icon={Map}
          title="Build a trip"
          desc="Generate a day-by-day itinerary with AI, then review it."
        />
        <ActionCard
          to="/app/trips"
          icon={Sparkles}
          title="Create posters & captions"
          desc="Turn any approved trip into marketing creatives."
        />
        <ActionCard
          to="/app/approvals"
          icon={CheckCircle2}
          title="Review the queue"
          desc="Approve or reject what the agents drafted."
          badge={pending ? `${pending} pending` : undefined}
        />
      </motion.div>
    </div>
  );
}

function ActionCard({
  to,
  icon: Icon,
  title,
  desc,
  badge,
}: {
  to: string;
  icon: typeof Map;
  title: string;
  desc: string;
  badge?: string;
}) {
  return (
    <motion.div variants={fadeUp} whileHover={{ y: -4 }}>
      <Link
        to={to}
        className="group block rounded-2xl border border-black/5 bg-white p-6 transition hover:shadow-lg hover:shadow-black/5"
      >
        <div className="mb-4 flex items-center justify-between">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--color-ocean-50)]">
            <Icon className="h-5 w-5 text-[var(--color-ocean-600)]" />
          </div>
          {badge && (
            <span className="rounded-full bg-[var(--color-sunset-500)]/10 px-2.5 py-1 text-xs font-medium text-[var(--color-sunset-500)]">
              {badge}
            </span>
          )}
        </div>
        <h3 className="font-semibold">{title}</h3>
        <p className="mt-1 text-sm text-black/55">{desc}</p>
        <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-ocean-600)]">
          Open <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
        </span>
      </Link>
    </motion.div>
  );
}
