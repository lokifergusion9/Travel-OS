import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Globe } from "lucide-react";
import type { ReactNode } from "react";
import { pageVariants, scaleIn } from "@/lib/motion";

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="aurora flex min-h-screen items-center justify-center px-6 py-12 text-white"
    >
      <motion.div
        variants={scaleIn}
        initial="initial"
        animate="animate"
        className="glass w-full max-w-md rounded-3xl p-8"
      >
        <Link to="/" className="mb-8 flex items-center gap-2 font-semibold">
          <Globe className="h-6 w-6 text-[var(--color-teal-400)]" />
          TravelOS
        </Link>
        <h1 className="text-2xl font-bold">{title}</h1>
        <p className="mt-1 mb-6 text-sm text-white/60">{subtitle}</p>
        {children}
        <div className="mt-6 text-center text-sm text-white/60">{footer}</div>
      </motion.div>
    </motion.div>
  );
}
