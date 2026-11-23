import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authApi } from "../api";
import { refreshSession, setAccessToken, setAuthLostHandler } from "../api/client";
import type { User } from "../types";

export interface AuthValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  restoreSession: () => Promise<boolean>;
  setUser: (u: User | null) => void;
}
export const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const restoreSession = useCallback(async () => {
    const token = await refreshSession();
    if (!token) { setUser(null); return false; }
    try { setUser(await authApi.me()); return true; } catch { setUser(null); return false; }
  }, []);

  useEffect(() => {
    restoreSession().finally(() => setLoading(false));
    setAuthLostHandler(() => { setUser(null); qc.clear(); });
    return () => setAuthLostHandler(null);
  }, [restoreSession, qc]);

  const value = useMemo<AuthValue>(() => ({
    user, loading, setUser, restoreSession,
    login: async (email, password) => {
      const t = await authApi.login({ email, password });
      setAccessToken(t.access_token);
      setUser(await authApi.me());
    },
    register: async (email, password, name) => {
      const t = await authApi.register({ email, password, name });
      setAccessToken(t.access_token);
      setUser(await authApi.me());
    },
    logout: async () => {
      try { await authApi.logout(); } catch { /* session may already be gone */ }
      setAccessToken(null); setUser(null); qc.clear();
    },
  }), [user, loading, restoreSession, qc]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth(): AuthValue {
  const c = useContext(AuthContext);
  if (!c) throw new Error("useAuth must be used inside AuthProvider");
  return c;
}
