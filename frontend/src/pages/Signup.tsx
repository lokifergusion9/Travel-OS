import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { AuthLayout } from "@/components/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { useAuth } from "@/lib/auth";

export function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    agency_name: "",
    full_name: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const update = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signup(form);
      navigate("/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      title="Create your agency"
      subtitle="Spin up your TravelOS workspace in seconds."
      footer={
        <>
          Already onboard?{" "}
          <Link to="/login" className="text-[var(--color-ocean-400)] hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <Field
          label="Agency name"
          placeholder="Himalaya Treks"
          required
          value={form.agency_name}
          onChange={update("agency_name")}
        />
        <Field
          label="Your name"
          placeholder="Aadi"
          required
          value={form.full_name}
          onChange={update("full_name")}
        />
        <Field
          label="Email"
          type="email"
          placeholder="you@agency.com"
          required
          value={form.email}
          onChange={update("email")}
        />
        <Field
          label="Password"
          type="password"
          placeholder="At least 8 characters"
          required
          minLength={8}
          value={form.password}
          onChange={update("password")}
        />
        {error && <p className="text-sm text-[var(--color-sunset-400)]">{error}</p>}
        <Button type="submit" disabled={busy} className="w-full">
          {busy ? "Creating…" : "Create workspace"} <ArrowRight className="h-4 w-4" />
        </Button>
      </form>
    </AuthLayout>
  );
}
