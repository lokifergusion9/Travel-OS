import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, refreshTokens, tokenStore } from "./api";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "owner" | "member";
  tenant_id: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  onboarding_completed: boolean;
  auto_followup: boolean;
  created_at: string;
}

interface Me {
  user: User;
  tenant: Tenant;
}

interface AuthState {
  user: User | null;
  tenant: Tenant | null;
  loading: boolean;
  signup: (data: SignupData) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
  setTenant: (t: Tenant) => void;
}

interface SignupData {
  agency_name: string;
  full_name: string;
  email: string;
  password: string;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tenant, setTenantState] = useState<Tenant | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    // After a reload the access token is gone; restore it from the cookie.
    if (!tokenStore.access && !(await refreshTokens())) {
      setLoading(false);
      return;
    }
    try {
      const me = await api<Me>("/api/v1/auth/me");
      setUser(me.user);
      setTenantState(me.tenant);
    } catch {
      tokenStore.clear();
      setUser(null);
      setTenantState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const signup = useCallback(
    async (data: SignupData) => {
      const tokens = await api<{ access_token: string; refresh_token: string }>(
        "/api/v1/auth/signup",
        { method: "POST", body: JSON.stringify(data), auth: false },
      );
      tokenStore.set(tokens);
      await refreshMe();
    },
    [refreshMe],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await api<{ access_token: string; refresh_token: string }>(
        "/api/v1/auth/login",
        { method: "POST", body: JSON.stringify({ email, password }), auth: false },
      );
      tokenStore.set(tokens);
      await refreshMe();
    },
    [refreshMe],
  );

  const logout = useCallback(async () => {
    try {
      // Revokes the tokens server-side and clears the refresh cookie.
      await api("/api/v1/auth/logout", { method: "POST", retry: false });
    } catch {
      /* already logged out / offline — clear locally regardless */
    }
    tokenStore.clear();
    setUser(null);
    setTenantState(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        tenant,
        loading,
        signup,
        login,
        logout,
        refreshMe,
        setTenant: setTenantState,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
