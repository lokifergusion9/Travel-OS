import { motion } from "framer-motion";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Map,
  CheckCircle2,
  Hotel,
  Megaphone,
  Users,
  BarChart3,
  Settings,
  Globe,
  LogOut,
} from "lucide-react";
import { useAuth } from "@/lib/auth";

const links = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/trips", label: "Trips", icon: Map, end: false },
  { to: "/app/sourcing", label: "Sourcing", icon: Hotel, end: false },
  { to: "/app/publishing", label: "Publishing", icon: Megaphone, end: false },
  { to: "/app/leads", label: "Leads", icon: Users, end: false },
  { to: "/app/analytics", label: "Analytics", icon: BarChart3, end: false },
  { to: "/app/approvals", label: "Approvals", icon: CheckCircle2, end: false },
];

const soon = [{ label: "Settings", icon: Settings }];

export function DashboardLayout() {
  const { user, tenant, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-[#f7f9fc] text-[var(--color-ink)]">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-black/5 bg-white px-4 py-6 md:flex">
        <div className="mb-8 flex items-center gap-2 px-2 font-semibold">
          <Globe className="h-6 w-6 text-[var(--color-ocean-500)]" />
          TravelOS
        </div>
        <nav className="flex-1 space-y-1">
          {links.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className="relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-black/60 transition hover:text-black"
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-xl bg-[var(--color-ocean-50)]"
                      transition={{ type: "spring", stiffness: 400, damping: 32 }}
                    />
                  )}
                  <item.icon
                    className={`relative h-4.5 w-4.5 ${isActive ? "text-[var(--color-ocean-600)]" : ""}`}
                  />
                  <span className={`relative ${isActive ? "text-[var(--color-ocean-600)]" : ""}`}>
                    {item.label}
                  </span>
                </>
              )}
            </NavLink>
          ))}
          <div className="mt-4 mb-2 px-3 text-[11px] font-semibold uppercase tracking-wide text-black/30">
            Coming soon
          </div>
          {soon.map((item) => (
            <div
              key={item.label}
              className="flex cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-black/30"
            >
              <item.icon className="h-4.5 w-4.5" />
              {item.label}
            </div>
          ))}
        </nav>
        <button
          onClick={logout}
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-black/50 transition hover:bg-black/5 hover:text-black"
        >
          <LogOut className="h-4 w-4" /> Log out
        </button>
      </aside>

      <main className="flex-1 px-6 py-8 sm:px-10">
        <header className="mb-8 flex items-center justify-between">
          <div>
            <p className="text-sm text-black/50">{tenant?.name}</p>
            <h1 className="text-2xl font-bold">
              Welcome back, {user?.full_name?.split(" ")[0]} 👋
            </h1>
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-[var(--color-teal-400)] to-[var(--color-ocean-500)] font-semibold text-white">
            {user?.full_name?.[0]?.toUpperCase()}
          </div>
        </header>
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        >
          <Outlet />
        </motion.div>
      </main>
    </div>
  );
}
