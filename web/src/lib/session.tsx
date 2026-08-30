"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { ApiError, api } from "./api";
import type { Profile } from "./types";

interface SessionValue {
  profile: Profile | null;
  loading: boolean;
  refresh: () => Promise<void>;
  setProfile: (p: Profile) => void;
  logout: () => Promise<void>;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setProfile(await api.get<Profile>("/auth/me"));
    } catch (error) {
      // 401 is the normal logged-out state, not a failure worth surfacing.
      if (!(error instanceof ApiError) || error.status !== 401) console.error(error);
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    await api.post("/auth/logout");
    setProfile(null);
  }, []);

  return (
    <SessionContext.Provider value={{ profile, loading, refresh, setProfile, logout }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}
