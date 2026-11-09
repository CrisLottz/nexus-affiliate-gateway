import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, setCsrfToken, type AppConfig, type User } from "./api";

// Loads the white-label config and the current user once, and exposes login/logout.

interface AppState {
  config: AppConfig | null;
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const loadConfig = api<AppConfig>("/api/config").then((c) => {
      setConfig(c);
      document.title = c.brand_name;
      document.documentElement.style.setProperty("--brand", c.brand_primary_color);
    });
    const loadUser = api<{ user: User }>("/api/auth/me")
      .then((r) => setUser(r.user))
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 401)) throw e;
      });
    Promise.allSettled([loadConfig, loadUser]).then(() => setReady(true));
  }, []);

  const login = async (email: string, password: string) => {
    const r = await api<{ user: User; csrf_token: string }>("/api/auth/login", {
      method: "POST",
      body: { email, password },
    });
    setCsrfToken(r.csrf_token); // the session changed, so did the token
    setUser(r.user);
  };

  const logout = async () => {
    await api("/api/auth/logout", { method: "POST" });
    setUser(null);
  };

  return (
    <AppContext.Provider value={{ config, user, ready, login, logout }}>{children}</AppContext.Provider>
  );
}

export function useApp(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp outside AppProvider");
  return ctx;
}
