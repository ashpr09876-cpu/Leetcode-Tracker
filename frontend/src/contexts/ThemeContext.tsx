import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

export type ThemeChoice = "light" | "dark" | "system";
interface Ctx { theme: ThemeChoice; setTheme: (t: ThemeChoice) => void; cycle: () => void }
const ThemeCtx = createContext<Ctx | null>(null);
const KEY = "ct-theme"; // theme choice is not private data, so localStorage is fine

function read(): ThemeChoice {
  try { const v = localStorage.getItem(KEY); if (v === "light" || v === "dark" || v === "system") return v; } catch { /* ignore */ }
  return "system";
}
function apply(t: ThemeChoice) {
  const dark = t === "dark" || (t === "system" && window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", !!dark);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeChoice>(read);
  const setTheme = useCallback((t: ThemeChoice) => {
    setThemeState(t);
    try { localStorage.setItem(KEY, t); } catch { /* ignore */ }
  }, []);
  useEffect(() => {
    apply(theme);
    if (theme !== "system" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const fn = () => apply("system");
    mq.addEventListener?.("change", fn);
    return () => mq.removeEventListener?.("change", fn);
  }, [theme]);
  const cycle = useCallback(() => setTheme(theme === "light" ? "dark" : theme === "dark" ? "system" : "light"), [theme, setTheme]);
  return <ThemeCtx.Provider value={{ theme, setTheme, cycle }}>{children}</ThemeCtx.Provider>;
}
export function useTheme() {
  const c = useContext(ThemeCtx);
  if (!c) throw new Error("useTheme must be used inside ThemeProvider");
  return c;
}
