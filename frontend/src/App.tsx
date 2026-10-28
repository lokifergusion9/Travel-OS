import { AnimatePresence } from "framer-motion";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Landing } from "@/pages/Landing";
import { Signup } from "@/pages/Signup";
import { Login } from "@/pages/Login";
import { Onboarding } from "@/pages/Onboarding";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Overview } from "@/pages/dashboard/Overview";
import { Trips } from "@/pages/dashboard/Trips";
import { TripDetail } from "@/pages/dashboard/TripDetail";
import { Leads } from "@/pages/dashboard/Leads";
import { Sourcing } from "@/pages/dashboard/Sourcing";
import { Publishing } from "@/pages/dashboard/Publishing";
import { Analytics } from "@/pages/dashboard/Analytics";
import { Approvals } from "@/pages/dashboard/Approvals";
import type { ReactNode } from "react";

function Loader() {
  return (
    <div className="aurora flex min-h-screen items-center justify-center">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-white/20 border-t-white" />
    </div>
  );
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loader />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const location = useLocation();
  // Keep the dashboard shell mounted across its sub-routes (the Outlet animates
  // those); only animate top-level page swaps.
  const key = location.pathname.startsWith("/app") ? "/app" : location.pathname;
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={key}>
        <Route path="/" element={<Landing />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login />} />
        <Route
          path="/onboarding"
          element={
            <RequireAuth>
              <Onboarding />
            </RequireAuth>
          }
        />
        <Route
          path="/app"
          element={
            <RequireAuth>
              <DashboardLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Overview />} />
          <Route path="trips" element={<Trips />} />
          <Route path="trips/:id" element={<TripDetail />} />
          <Route path="leads" element={<Leads />} />
          <Route path="sourcing" element={<Sourcing />} />
          <Route path="publishing" element={<Publishing />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="approvals" element={<Approvals />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
}
