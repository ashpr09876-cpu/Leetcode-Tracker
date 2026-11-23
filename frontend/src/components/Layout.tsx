import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { BarChart3, Building2, CalendarClock, Code2, LayoutDashboard, ListChecks, LogOut, Menu, Monitor, Moon, Settings, ShieldCheck, Sparkles, Sun, Target, X } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/problems", label: "Problems", icon: ListChecks },
  { to: "/revisions", label: "Revisions", icon: CalendarClock },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/topics", label: "Topics", icon: Code2 },
  { to: "/goals", label: "Goals", icon: Target },
  { to: "/companies", label: "Interview prep", icon: Building2 },
  { to: "/ai", label: "AI Coach", icon: Sparkles },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { theme, cycle } = useTheme();
  const [open, setOpen] = useState(false);
  const ThemeIcon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;
  const items = user?.is_admin ? [...NAV, { to: "/admin", label: "Admin", icon: ShieldCheck }] : NAV;

  const nav = (
    <nav aria-label="Main navigation" className="flex flex-1 flex-col gap-1">
      {items.map(({ to, label, icon: Icon, ...rest }) => (
        <NavLink key={to} to={to} end={"end" in rest} onClick={() => setOpen(false)}
          className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-accent/15 text-accent" : "text-muted hover:bg-hover hover:text-fg"}`}>
          <Icon className="h-4 w-4" aria-hidden />{label}
        </NavLink>
      ))}
    </nav>
  );
  const footer = (
    <div className="space-y-1 border-t border-line pt-3">
      <p className="truncate px-3 text-xs text-muted" title={user?.email}>{user?.name || user?.email}</p>
      <button onClick={cycle} aria-label={`Theme: ${theme}. Click to change`} className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted hover:bg-hover hover:text-fg">
        <ThemeIcon className="h-4 w-4" aria-hidden />Theme: {theme}
      </button>
      <button onClick={() => logout()} className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted hover:bg-hover hover:text-fg">
        <LogOut className="h-4 w-4" aria-hidden />Log out
      </button>
    </div>
  );
  const brand = <div className="mb-4 flex items-center gap-2 px-3 text-lg font-semibold"><span className="grid h-7 w-7 place-items-center rounded-lg bg-accent text-accent-fg"><Code2 className="h-4 w-4" /></span>CodeTrack</div>;

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
      <aside className="sticky top-0 hidden h-screen flex-col border-r border-line bg-card p-3 lg:flex">{brand}{nav}{footer}</aside>
      <header className="flex items-center justify-between border-b border-line bg-card px-4 py-3 lg:hidden">
        <div className="flex items-center gap-2 font-semibold"><Code2 className="h-5 w-5 text-accent" />CodeTrack</div>
        <button aria-label="Open menu" onClick={() => setOpen(true)} className="rounded p-1 hover:bg-hover"><Menu className="h-5 w-5" /></button>
      </header>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-0 flex h-full w-64 flex-col bg-card p-3">
            <button aria-label="Close menu" onClick={() => setOpen(false)} className="mb-2 self-end rounded p-1 hover:bg-hover"><X className="h-5 w-5" /></button>
            {brand}{nav}{footer}
          </div>
        </div>
      )}
      <main className="mx-auto w-full max-w-6xl p-4 sm:p-6"><Outlet /></main>
    </div>
  );
}
