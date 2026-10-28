import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "ghost" | "outline";

interface Props {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: Variant;
  disabled?: boolean;
  className?: string;
}

const styles: Record<Variant, string> = {
  primary:
    "bg-gradient-to-r from-[var(--color-teal-400)] via-[var(--color-ocean-500)] to-[var(--color-sunset-500)] text-white shadow-lg shadow-[var(--color-ocean-500)]/25",
  ghost: "bg-white/10 text-white hover:bg-white/20",
  outline:
    "border border-white/25 text-white hover:bg-white/10 backdrop-blur",
};

export function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled,
  className,
}: Props) {
  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={disabled}
      whileHover={{ scale: disabled ? 1 : 1.03 }}
      whileTap={{ scale: disabled ? 1 : 0.97 }}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
        styles[variant],
        className,
      )}
    >
      {children}
    </motion.button>
  );
}
