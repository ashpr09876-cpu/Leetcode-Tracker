import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, SkipForward, Trash2 } from "lucide-react";
import { problemApi, revisionApi } from "../api";
import { errMsg } from "../api/client";
import { useToast } from "../contexts/ToastContext";
import { Badge, Button, Card, EmptyState, ErrorState, Field, Input, LoadingBlock, PageHeader, Select } from "../components/ui";
import { diffColor, fmtDate } from "../utils/format";

export default function Revisions() {
  const [tab, setTab] = useState<"pending" | "completed" | "skipped">("pending");
  const [problemId, setProblemId] = useState("");
  const [priority, setPriority] = useState("medium");
  const [due, setDue] = useState("");
  const toast = useToast();
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["revisions", tab], queryFn: () => revisionApi.list({ status: tab }) });
  const problems = useQuery({ queryKey: ["problems", "all-for-revision"], queryFn: () => problemApi.list({ page_size: 100, sort: "title" }) });
  const refresh = () => { qc.invalidateQueries({ queryKey: ["revisions"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); qc.invalidateQueries({ queryKey: ["analytics"] }); };
  const onError = (e: unknown) => toast.error(errMsg(e));
  const create = useMutation({ mutationFn: () => revisionApi.create({ problem_id: Number(problemId), priority, due_date: due || null }), onSuccess: () => { toast.success("Revision scheduled"); setProblemId(""); setDue(""); refresh(); }, onError });
  const update = useMutation({ mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) => revisionApi.update(id, body), onSuccess: (_, v) => { if (v.body.status === "completed") toast.success("Marked as revised - next revision scheduled if stages remain"); refresh(); }, onError });
  const remove = useMutation({ mutationFn: (id: number) => revisionApi.remove(id), onSuccess: refresh, onError });
  const prio = { high: "text-hard", medium: "text-medium", low: "text-muted" } as const;

  return (
    <>
      <PageHeader title="Revisions" subtitle="Spaced repetition: intervals are configurable in Settings." />
      <Card className="mb-4">
        <form className="grid gap-3 sm:grid-cols-5 sm:items-end" onSubmit={(e) => { e.preventDefault(); if (problemId) create.mutate(); }}>
          <div className="sm:col-span-2"><Field label="Problem" htmlFor="rv-problem"><Select id="rv-problem" value={problemId} onChange={(e) => setProblemId(e.target.value)}><option value="">Select a problem...</option>{problems.data?.items.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}</Select></Field></div>
          <Field label="Priority" htmlFor="rv-prio"><Select id="rv-prio" value={priority} onChange={(e) => setPriority(e.target.value)}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></Select></Field>
          <Field label="Due date" htmlFor="rv-due" hint="Blank = first interval"><Input id="rv-due" type="date" value={due} onChange={(e) => setDue(e.target.value)} /></Field>
          <Button type="submit" disabled={!problemId} loading={create.isPending}>Schedule</Button>
        </form>
      </Card>
      <div role="tablist" className="mb-3 flex gap-1">
        {(["pending", "completed", "skipped"] as const).map((t) => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)} className={`rounded-lg px-3 py-1.5 text-sm capitalize ${tab === t ? "bg-accent/15 text-accent" : "text-muted hover:bg-hover"}`}>{t === "pending" ? "Queue" : t}</button>)}
      </div>
      <Card className="p-0">
        {list.isLoading ? <div className="p-4"><LoadingBlock /></div> : list.isError ? <ErrorState message={errMsg(list.error)} onRetry={() => list.refetch()} /> :
          !list.data?.length ? <EmptyState title={tab === "pending" ? "Your revision queue is empty" : `No ${tab} revisions`} text={tab === "pending" ? "Schedule a problem above, or from its detail page." : undefined} /> : (
            <ul className="divide-y divide-line">{list.data.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center gap-3 p-3 text-sm">
                <div className="min-w-0 flex-1"><Link to={`/problems/${r.problem_id}`} className="font-medium hover:underline">{r.problem_title}</Link>
                  <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs"><span className={`capitalize ${diffColor[r.problem_difficulty]}`}>{r.problem_difficulty}</span><span className={`capitalize ${prio[r.priority]}`}>{r.priority} priority</span><Badge>stage {r.stage + 1}</Badge>{r.overdue && <Badge className="border-hard text-hard">Overdue</Badge>}</div></div>
                {r.status === "pending" ? (<>
                  <Input aria-label={`Due date for ${r.problem_title}`} type="date" className="w-40" defaultValue={r.due_date} onBlur={(e) => e.target.value && e.target.value !== r.due_date && update.mutate({ id: r.id, body: { due_date: e.target.value } })} />
                  <Button variant="secondary" onClick={() => update.mutate({ id: r.id, body: { status: "completed" } })}><Check className="h-4 w-4" />Revised</Button>
                  <Button variant="ghost" aria-label={`Skip ${r.problem_title}`} onClick={() => update.mutate({ id: r.id, body: { status: "skipped" } })}><SkipForward className="h-4 w-4" /></Button>
                </>) : <span className="text-muted">{r.status === "completed" ? `Revised ${fmtDate(r.completed_at)}` : `Due ${fmtDate(r.due_date)}`}</span>}
                <Button variant="ghost" aria-label={`Delete revision for ${r.problem_title}`} onClick={() => remove.mutate(r.id)}><Trash2 className="h-4 w-4" /></Button>
              </li>))}</ul>)}
      </Card>
    </>
  );
}
