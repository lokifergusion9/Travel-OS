import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  Map,
  Sparkles,
  Hotel,
  Megaphone,
  Users,
  ArrowRight,
  Globe,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { fadeUp, pageVariants, staggerContainer } from "@/lib/motion";

const modules = [
  { icon: Map, title: "Itinerary AI", desc: "Day-by-day treks in seconds." },
  { icon: Sparkles, title: "Creative Studio", desc: "Posters, captions, brochures." },
  { icon: Hotel, title: "Sourcing", desc: "Hotel & transport outreach." },
  { icon: Megaphone, title: "Publishing", desc: "Instagram & WhatsApp." },
  { icon: Users, title: "CRM + Leads", desc: "Auto-followup till deal close." },
];

export function Landing() {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="aurora min-h-screen overflow-hidden text-white"
    >
      {/* Nav */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2 font-semibold">
          <Globe className="h-6 w-6 text-[var(--color-teal-400)]" />
          TravelOS
        </div>
        <div className="flex items-center gap-3 text-sm">
          <Link to="/login" className="text-white/70 hover:text-white">
            Log in
          </Link>
          <Link to="/signup">
            <Button variant="outline" className="px-4 py-2">
              Get started
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero */}
      <motion.section
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="mx-auto max-w-4xl px-6 pt-16 pb-10 text-center"
      >
        <motion.div
          variants={fadeUp}
          className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-1.5 text-xs text-white/70"
        >
          <Sparkles className="h-3.5 w-3.5 text-[var(--color-sunset-400)]" />
          AI agents + CRM for travel agencies
        </motion.div>
        <motion.h1
          variants={fadeUp}
          className="text-5xl font-extrabold leading-tight tracking-tight sm:text-6xl"
        >
          Run your whole agency
          <br />
          on <span className="gradient-text">autopilot</span>
        </motion.h1>
        <motion.p
          variants={fadeUp}
          className="mx-auto mt-6 max-w-2xl text-lg text-white/65"
        >
          From a new trek to a closed booking — itineraries, posters, hotel deals,
          Instagram ads, and lead followups. Agents do the work, you approve.
        </motion.p>
        <motion.div variants={fadeUp} className="mt-9 flex justify-center gap-4">
          <Link to="/signup">
            <Button className="px-7 py-3.5 text-base">
              Start free <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link to="/login">
            <Button variant="ghost" className="px-7 py-3.5 text-base">
              I have an account
            </Button>
          </Link>
        </motion.div>
      </motion.section>

      {/* Module cards */}
      <motion.section
        variants={staggerContainer}
        initial="initial"
        whileInView="animate"
        viewport={{ once: true, amount: 0.3 }}
        className="mx-auto grid max-w-6xl grid-cols-1 gap-4 px-6 pb-24 sm:grid-cols-2 lg:grid-cols-5"
      >
        {modules.map((m) => (
          <motion.div
            key={m.title}
            variants={fadeUp}
            whileHover={{ y: -6 }}
            className="glass rounded-2xl p-5"
          >
            <m.icon className="mb-3 h-7 w-7 text-[var(--color-ocean-400)]" />
            <h3 className="font-semibold">{m.title}</h3>
            <p className="mt-1 text-sm text-white/55">{m.desc}</p>
          </motion.div>
        ))}
      </motion.section>
    </motion.div>
  );
}
