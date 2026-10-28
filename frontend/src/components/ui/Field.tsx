import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Field({ label, className, ...props }: Props) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-white/60">
        {label}
      </span>
      <input
        {...props}
        className={cn(
          "w-full rounded-xl border border-white/15 bg-white/5 px-4 py-3 text-white placeholder-white/30",
          "outline-none transition focus:border-[var(--color-ocean-400)] focus:bg-white/10 focus:ring-2 focus:ring-[var(--color-ocean-400)]/40",
          className,
        )}
      />
    </label>
  );
}
