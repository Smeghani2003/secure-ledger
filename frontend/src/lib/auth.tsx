import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { api } from "./api";

type Tokens = { access_token: string; refresh_token: string };

type AuthContextValue = {
  token: string | null;
  signup: (email: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = "secureledger.access_token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    typeof window !== "undefined" ? sessionStorage.getItem(STORAGE_KEY) : null,
  );

  const persist = useCallback((t: string | null) => {
    setToken(t);
    if (t) sessionStorage.setItem(STORAGE_KEY, t);
    else sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  const signup = useCallback(
    async (email: string, password: string) => {
      const t = await api<Tokens>("/api/auth/signup", {
        method: "POST",
        body: { email, password },
      });
      persist(t.access_token);
    },
    [persist],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const t = await api<Tokens>("/api/auth/login", {
        method: "POST",
        body: { email, password },
      });
      persist(t.access_token);
    },
    [persist],
  );

  const logout = useCallback(() => persist(null), [persist]);

  const value = useMemo(() => ({ token, signup, login, logout }), [token, signup, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
