import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi, lcApi, userApi } from "../api";
import { errMsg } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import { useTheme, type ThemeChoice } from "../contexts/ThemeContext";
import { useToast } from "../contexts/ToastContext";
import { Button, Card, ConfirmDialog, Field, Input, PageHeader, Select } from "../components/ui";
import { fmtDateTime } from "../utils/format";

const zones: string[] = (() => { try { return (Intl as unknown as { supportedValuesOf: (k: string) => string[] }).supportedValuesOf("timeZone"); } catch { return ["UTC"]; } })();

export default function Settings() {
  const { user, setUser, logout } = useAuth();
  const { setTheme } = useTheme();
  const toast = useToast();
  const qc = useQueryClient();
  const ai = useQuery({ queryKey: ["ai-status"], queryFn: aiApi.status });
  const lc = useQuery({ queryKey: ["lc-status"], queryFn: lcApi.status });
  const [name, setName] = useState(user?.name ?? "");
  const [tz, setTz] = useState(user?.timezone ?? "UTC");
  const [goal, setGoal] = useState(String(user?.preferences?.daily_goal ?? 1));
  const [notif, setNotif] = useState(user?.preferences?.notifications_enabled ?? true);
  const [provider, setProvider] = useState(user?.preferences?.ai_provider ?? "");
  const [themeSel, setThemeSel] = useState<ThemeChoice>(user?.preferences?.theme ?? "system");
  const [intervals, setIntervals] = useState((user?.preferences?.revision_intervals ?? [1, 3, 7, 14, 30, 60]).join(", "));
  const [lcName, setLcName] = useState(user?.leetcode_username ?? "");
  const [curPw, setCurPw] = useState(""); const [newPw, setNewPw] = useState("");
  const [delOpen, setDelOpen] = useState(false); const [delText, setDelText] = useState("");
  const onError = (e: unknown) => toast.error(errMsg(e));

  const save = useMutation({
    mutationFn: () => {
      const parsed = intervals.split(",").map((x) => Number(x.trim())).filter((n) => n > 0);
      if (!parsed.length || parsed.some((n) => !Number.isInteger(n))) throw new Error("Revision intervals must be whole numbers of days, e.g. 1, 3, 7, 14");
      return userApi.update({ name, timezone: tz, preferences: { theme: themeSel, daily_goal: Number(goal), notifications_enabled: notif, ai_provider: provider, revision_intervals: parsed } });
    },
    onSuccess: (u) => { setUser(u); setTheme(themeSel); toast.success("Settings saved"); qc.invalidateQueries({ queryKey: ["dashboard"] }); qc.invalidateQueries({ queryKey: ["ai-status"] }); }, onError,
  });
  const pw = useMutation({ mutationFn: () => userApi.update({ current_password: curPw || null, new_password: newPw }), onSuccess: () => { toast.success("Password changed. Other sessions were signed out."); setCurPw(""); setNewPw(""); }, onError });
  const connect = useMutation({ mutationFn: () => lcApi.connect(lcName.trim()), onSuccess: () => { toast.success("LeetCode username connected"); qc.invalidateQueries({ queryKey: ["lc-status"] }); }, onError });
  const sync = useMutation({
    mutationFn: lcApi.sync,
    onSuccess: (r) => { toast.success(`Sync finished: ${r.imported} imported, ${r.skipped_existing} already tracked`); for (const k of ["lc-status", "problems", "dashboard", "analytics"]) qc.invalidateQueries({ queryKey: [k] }); },
    onError: (e) => { toast.error(errMsg(e)); qc.invalidateQueries({ queryKey: ["lc-status"] }); },
  });
  const disconnect = useMutation({ mutationFn: lcApi.disconnect, onSuccess: () => { toast.success("LeetCode disconnected"); qc.invalidateQueries({ queryKey: ["lc-status"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); }, onError });
  const del = useMutation({ mutationFn: userApi.remove, onSuccess: () => logout(), onError });

  return (
    <>
      <PageHeader title="Settings" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-3">
          <h2 className="font-semibold">Profile &amp; preferences</h2>
          <Field label="Name" htmlFor="s-name"><Input id="s-name" value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label="Email" htmlFor="s-email"><Input id="s-email" value={user?.email ?? ""} disabled readOnly /></Field>
          <Field label="Timezone" htmlFor="s-tz" hint="Streaks and daily activity use this timezone."><Select id="s-tz" value={tz} onChange={(e) => setTz(e.target.value)}>{(zones.includes(tz) ? zones : [tz, ...zones]).map((z) => <option key={z}>{z}</option>)}</Select></Field>
          <Field label="Theme" htmlFor="s-theme"><Select id="s-theme" value={themeSel} onChange={(e) => { const v = e.target.value as ThemeChoice; setThemeSel(v); setTheme(v); }}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></Select></Field>
          <Field label="Daily goal (problems solved)" htmlFor="s-goal"><Input id="s-goal" type="number" min={0} max={100} value={goal} onChange={(e) => setGoal(e.target.value)} /></Field>
          <Field label="Revision intervals (days)" htmlFor="s-int" hint="Spaced-repetition schedule, e.g. 1, 3, 7, 14, 30, 60"><Input id="s-int" value={intervals} onChange={(e) => setIntervals(e.target.value)} /></Field>
          <Field label="AI provider" htmlFor="s-ai" hint={ai.data ? (ai.data.available_providers.length ? `Configured on server: ${ai.data.available_providers.join(", ")}` : "No provider is configured on the server (set keys in backend/.env).") : undefined}>
            <Select id="s-ai" value={provider} onChange={(e) => setProvider(e.target.value)}><option value="">Server default</option>{["ollama", "gemini", "openai", "anthropic"].map((p) => <option key={p} value={p}>{p}</option>)}</Select></Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={notif} onChange={(e) => setNotif(e.target.checked)} />Enable notifications <span className="text-xs text-muted">(preference is saved; reminder delivery is not implemented yet)</span></label>
          <Button loading={save.isPending} onClick={() => save.mutate()}>Save settings</Button>
        </Card>

        <div className="space-y-4">
          <Card className="space-y-3">
            <h2 className="font-semibold">LeetCode integration</h2>
            <p className="text-xs text-muted">{lc.data?.disclaimer ?? "LeetCode has no official public API; sync is best-effort and optional."} Never enter passwords or cookies - only your public username is used.</p>
            <div className="flex gap-2"><Input aria-label="LeetCode username" placeholder="LeetCode username" value={lcName} onChange={(e) => setLcName(e.target.value)} /><Button variant="secondary" disabled={!lcName.trim()} loading={connect.isPending} onClick={() => connect.mutate()}>Connect</Button></div>
            {lc.data?.connected && (
              <div className="space-y-2 text-sm">
                <p>Connected as <strong>{lc.data.username}</strong>. Last successful sync: {lc.data.last_sync_at ? fmtDateTime(lc.data.last_sync_at) : "never"}.</p>
                {lc.data.last_error && <p role="alert" className="rounded-lg border border-hard/40 bg-hard/10 p-2 text-hard">Last sync error: {lc.data.last_error}</p>}
                <div className="flex gap-2"><Button loading={sync.isPending} onClick={() => sync.mutate()}>Sync now</Button><Button variant="secondary" loading={disconnect.isPending} onClick={() => disconnect.mutate()}>Disconnect</Button></div>
              </div>)}
          </Card>
          <Card className="space-y-3">
            <h2 className="font-semibold">Account security</h2>
            {user?.has_password && <Field label="Current password" htmlFor="s-cur"><Input id="s-cur" type="password" autoComplete="current-password" value={curPw} onChange={(e) => setCurPw(e.target.value)} /></Field>}
            <Field label="New password" htmlFor="s-new" hint="At least 8 characters. Changing it signs out other devices."><Input id="s-new" type="password" autoComplete="new-password" value={newPw} onChange={(e) => setNewPw(e.target.value)} /></Field>
            <Button variant="secondary" disabled={newPw.length < 8} loading={pw.isPending} onClick={() => pw.mutate()}>Change password</Button>
          </Card>
          <Card className="space-y-2 border-hard/40"><h2 className="font-semibold text-hard">Danger zone</h2><p className="text-sm text-muted">Permanently delete your account and all your data.</p><Button variant="danger" onClick={() => setDelOpen(true)}>Delete account</Button></Card>
        </div>
      </div>
      <ConfirmDialog open={delOpen} title="Delete your account?" message={`This cannot be undone. Type ${user?.email} to confirm.`} confirmLabel="Delete forever" loading={del.isPending} onConfirm={() => delText === user?.email ? del.mutate() : toast.error("The email does not match")} onClose={() => { setDelOpen(false); setDelText(""); }} />
      {delOpen && <div className="fixed inset-x-0 bottom-24 z-[60] mx-auto w-full max-w-xs px-4"><Input aria-label="Type your email to confirm" placeholder={user?.email} value={delText} onChange={(e) => setDelText(e.target.value)} /></div>}
    </>
  );
}
