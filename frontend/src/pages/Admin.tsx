import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api";
import { errMsg } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import { Badge, Button, Card, ErrorState, LoadingBlock, PageHeader } from "../components/ui";

export default function Admin() {
  const { user } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ["admin", "users"], queryFn: adminApi.users, enabled: !!user?.is_admin });
  const sys = useQuery({ queryKey: ["admin", "system"], queryFn: adminApi.system, enabled: !!user?.is_admin });
  const toggle = useMutation({ mutationFn: ({ id, active }: { id: number; active: boolean }) => adminApi.setActive(id, active), onSuccess: () => qc.invalidateQueries({ queryKey: ["admin"] }), onError: (e) => toast.error(errMsg(e)) });
  if (!user?.is_admin) return <ErrorState message="Administrator access is required." />;
  const ok = (v: string) => <Badge className={v === "ok" ? "border-easy text-easy" : "border-hard text-hard"}>{v}</Badge>;
  return (
    <>
      <PageHeader title="Admin" subtitle="Set ADMIN_EMAIL in backend/.env before registering to get an admin account." />
      <Card className="mb-4"><h2 className="mb-3 font-semibold">System health</h2>
        {sys.isLoading ? <LoadingBlock rows={2} /> : sys.isError ? <ErrorState message={errMsg(sys.error)} onRetry={() => sys.refetch()} /> : sys.data && (
          <div className="space-y-2 text-sm">
            <p className="flex flex-wrap gap-3">Database {ok(sys.data.database)} Redis {ok(sys.data.redis)} <span>AI providers: {sys.data.ai_providers_configured.join(", ") || "none configured"}</span> <span>API errors (24h): {sys.data.api_errors_24h}</span></p>
            {sys.data.leetcode_sync_errors.length > 0 && <div><p className="font-medium">LeetCode sync errors</p><ul className="text-muted">{sys.data.leetcode_sync_errors.map((e: any, i: number) => <li key={i}>{e.email}: {e.error}</li>)}</ul></div>}
            {sys.data.recent_api_errors.length > 0 && <div><p className="font-medium">Recent API errors</p><ul className="text-muted">{sys.data.recent_api_errors.map((e: any, i: number) => <li key={i}>{e.status} {e.path} - {e.message}</li>)}</ul></div>}
          </div>)}
      </Card>
      <Card className="p-0"><h2 className="p-4 pb-2 font-semibold">Users</h2>
        {users.isLoading ? <div className="p-4"><LoadingBlock /></div> : users.isError ? <ErrorState message={errMsg(users.error)} /> : (
          <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="border-b border-line text-left text-xs uppercase text-muted"><tr><th className="p-3">Email</th><th>Problems</th><th>Status</th><th className="p-3" /></tr></thead>
            <tbody>{users.data?.items.map((u) => <tr key={u.id} className="border-b border-line last:border-0"><td className="p-3">{u.email} {u.is_admin && <Badge>admin</Badge>}</td><td>{u.problem_count}</td><td>{u.is_active ? "Active" : "Disabled"}</td>
              <td className="p-3 text-right">{u.id !== user.id && <Button variant="secondary" onClick={() => toggle.mutate({ id: u.id, active: !u.is_active })}>{u.is_active ? "Disable" : "Enable"}</Button>}</td></tr>)}</tbody></table></div>)}
      </Card>
    </>
  );
}
