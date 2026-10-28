import type { Variants, Transition } from "framer-motion";

export const easeOut: Transition = { duration: 0.5, ease: [0.22, 1, 0.36, 1] };

/** Page-level enter/exit used with AnimatePresence in App. */
export const pageVariants: Variants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: easeOut },
  exit: { opacity: 0, y: -12, transition: { duration: 0.25 } },
};

/** Parent that staggers children in. */
export const staggerContainer: Variants = {
  initial: {},
  animate: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

export const fadeUp: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: easeOut },
};

export const scaleIn: Variants = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1, transition: easeOut },
};
