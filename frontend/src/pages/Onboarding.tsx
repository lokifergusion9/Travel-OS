import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  Map,
  Sparkles,
  Hotel,
  Megaphone,
  Users,
  Instagram,
  Mail,
  ArrowRight,
  ArrowLeft,
  Check,
  PartyPopper,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fadeUp, staggerContainer } from "@/lib/motion";

const slide = {
  enter: (dir: number) => ({ x: dir > 0 ? 80 : -80, opacity: 0 }),
  center: { x: 0, opacity: 1, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
  exit: (dir: number) => ({
    x: dir > 0 ? -80 : 80,
    opacity: 0,
    transition: { duration: 0.25 },
  }),
};

const automations = [
  { icon: Map, title: "Itineraries", color: "text-[var(--color-teal-400)]" },
  { icon: Sparkles, title: "Posters & captions", color: "text-[var(--color-sunset-400)]" },
  { icon: Hotel, title: "Hotel & transport deals", color: "text-[var(--color-ocean-400)]" },
  { icon: Megaphone, title: "Instagram publishing", color: "text-[var(--color-teal-400)]" },
  { icon: Users, title: "Lead followups", color: "text-[var(--color-sunset-400)]" },
];

export function Onboarding() {
  const { tenant, setTenant } = useAuth();
  const navigate = useNavigate();
  const [[step, dir], setStep] = useState<[number, number]>([0, 0]);
  const [finishing, setFinishing] = useState(false);
  const total = 3;

  const go = (next: number) => setStep([next, next > step ? 1 : -1]);

  async function finish() {
    setFinishing(true);
    try {
      const updated = await api<typeof tenant>("/api/v1/auth/onboarding", {
        method: "PATCH",
        body: JSON.stringify({ completed: true }),
      });
      if (updated) setTenant(updated);
      navigate("/app");
    } finally {
      setFinishing(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="aurora flex min-h-screen flex-col items-center justify-center px-6 text-white"
    >
      {/* Progress dots */}
      <div className="mb-10 flex gap-2">
        {Array.from({ length: total }).map((_, i) => (
          <motion.div
            key={i}
            animate={{
              width: i === step ? 32 : 10,
              backgroundColor: i <= step ? "#2dd4bf" : "rgba(255,255,255,0.2)",
            }}
            className="h-2.5 rounded-full"
          />
        ))}
      </div>

      <div className="relative w-full max-w-xl">
        <AnimatePresence mode="wait" custom={dir}>
          {step === 0 && (
            <motion.div
              key="welcome"
              custom={dir}
              variants={slide}
              initial="enter"
              animate="center"
              exit="exit"
              className="glass rounded-3xl p-10 text-center"
            >
              <PartyPopper className="mx-auto mb-4 h-12 w-12 text-[var(--color-sunset-400)]" />
              <h1 className="text-3xl font-bold">
                Welcome, <span className="gradient-text">{tenant?.name}</span>
              </h1>
              <p className="mx-auto mt-3 max-w-sm text-white/65">
                Your AI operations team is ready. Let's take a 30-second tour of what
                TravelOS will run for you.
              </p>
              <Button className="mt-8" onClick={() => go(1)}>
                Let's go <ArrowRight className="h-4 w-4" />
              </Button>
            </motion.div>
          )}

          {step === 1 && (
            <motion.div
              key="automations"
              custom={dir}
              variants={slide}
              initial="enter"
              animate="center"
              exit="exit"
              className="glass rounded-3xl p-10"
            >
              <h2 className="text-2xl font-bold">Here's what runs on autopilot</h2>
              <p className="mt-1 text-sm text-white/60">
                Every step has you in the loop — agents draft, you approve.
              </p>
              <motion.ul
                variants={staggerContainer}
                initial="initial"
                animate="animate"
                className="mt-6 space-y-3"
              >
                {automations.map((a) => (
                  <motion.li
                    key={a.title}
                    variants={fadeUp}
                    className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3"
                  >
                    <a.icon className={`h-5 w-5 ${a.color}`} />
                    <span className="font-medium">{a.title}</span>
                    <Check className="ml-auto h-4 w-4 text-[var(--color-teal-400)]" />
                  </motion.li>
                ))}
              </motion.ul>
              <div className="mt-8 flex justify-between">
                <Button variant="ghost" onClick={() => go(0)}>
                  <ArrowLeft className="h-4 w-4" /> Back
                </Button>
                <Button onClick={() => go(2)}>
                  Next <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="connect"
              custom={dir}
              variants={slide}
              initial="enter"
              animate="center"
              exit="exit"
              className="glass rounded-3xl p-10"
            >
              <h2 className="text-2xl font-bold">Connect your channels</h2>
              <p className="mt-1 text-sm text-white/60">
                Optional now — you can wire these up anytime from Settings.
              </p>
              <div className="mt-6 space-y-3">
                {[
                  { icon: Instagram, label: "Instagram Business", note: "Publish posters & capture leads" },
                  { icon: Mail, label: "Email / SMS", note: "Automated lead followups" },
                ].map((c) => (
                  <div
                    key={c.label}
                    className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3"
                  >
                    <c.icon className="h-5 w-5 text-[var(--color-ocean-400)]" />
                    <div>
                      <p className="font-medium">{c.label}</p>
                      <p className="text-xs text-white/50">{c.note}</p>
                    </div>
                    <span className="ml-auto rounded-full border border-white/15 px-3 py-1 text-xs text-white/50">
                      Later
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-8 flex justify-between">
                <Button variant="ghost" onClick={() => go(1)}>
                  <ArrowLeft className="h-4 w-4" /> Back
                </Button>
                <Button onClick={finish} disabled={finishing}>
                  {finishing ? "Setting up…" : "Enter dashboard"}{" "}
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
