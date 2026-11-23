import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Trash2 } from "lucide-react";
import { goalApi } from "../api";
import { errMsg } from "../api/client";
import { useToast } from "../contexts/ToastContext";
import { Button, Card, EmptyState, ErrorState, Field, Input, LoadingBlock, PageHeader, ProgressBar, Select } from "../components/ui";
import { fmtDate } from "../utils/format";
import type { Goal } from "../types";

function GoalRow({ g, onDelete }: { g: Goal; onDelete: () => void }) {
  return (
    <li className="space-y-2 py-3">
      <div className="flex items-center justify-between gap-2">
        <div><p className="flex items-center gap-1.5 font-medium">{g.completed && <CheckCircle2 className="h-4 w-4 text-easy" aria-label="Completed" />}{g.title}</p>
          <p className="text-xs capitalize text-muted">{g.period} - {g.metric} - {fmtDate(g.start_date)}{g.start_date !== g.end_date && ` to ${fmtDate(g.end_date)}`}</p></div>
        <button aria-label={`Delete goal ${g.title}`} className="rounded p-1.5 text-muted hover:bg-hover hover:text-hard" onClick={onDelete}><Trash2 className="h-4 w-4" /></button>
      </div>
      <ProgressBar value={g.progress} max={g.target} label={`${g.title} progress`} />
      <p className="text-xs text-muted">{g.progress} / {g.target}</p>
    </li>
  );
}

export default function Goals() {
  const [title, setTitle] = useState("");
  const [period, setPeriod] = useState("daily");
  const [metric, setMetric] = useState("solved");
  const [target, setTarget] = useState("1");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const toast = useToast();
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["goals"], queryFn: goalApi.list });
  const refresh = () => { qc.invalidateQueries({ queryKey: ["goals"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); };
  const create = useMutation({
    mutationFn: () => goalApi.create({ title: title.trim(), period, metric, target: Number(target), start_date: period === "custom" ? start : null, end_date: period === "custom" ? end : null }),
    onSuccess: () => { toast.success("Goal created"); setTitle(""); refresh(); }, onError: (e) => toast.error(errMsg(e)),
  });
  const remove = useMutation({ mutationFn: (id: number) => goalApi.remove(id), onSuccess: refresh, onError: (e) => toast.error(errMsg(e)) });
  const valid = title.trim() && Number(target) >= 1 && (period !== "custom" || (start && end));

  return (
    <>
      <PageHeader title="Goals" subtitle="Progress is counted from your logged activity." />
      <Card className="mb-4">
        <form className="grid gap-3 sm:grid-cols-6 sm:items-end" onSubmit={(e) => { e.preventDefault(); if (valid) create.mutate(); }}>
          <div className="sm:col-span-2"><Field label="Goal" htmlFor="g-title"><Input id="g-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Solve 3 mediums" maxLength={160} /></Field></div>
          <Field label="Period" htmlFor="g-period"><Select id="g-period" value={period} onChange={(e) => setPeriod(e.target.value)}><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="custom">Custom range</option></Select></Field>
          <Field label="Counts" htmlFor="g-metric"><Select id="g-metric" value={metric} onChange={(e) => setMetric(e.target.value)}><option value="solved">Problems solved</option><option value="attempts">Attempts</option></Select></Field>
          <Field label="Target" htmlFor="g-target"><Input id="g-target" type="number" min={1} value={target} onChange={(e) => setTarget(e.target.value)} /></Field>
          <Button type="submit" disabled={!valid} loading={create.isPending}>Create</Button>
          {period === "custom" && <>
            <Field label="Start" htmlFor="g-start"><Input id="g-start" type="date" value={start} onChange={(e) => setStart(e.target.value)} /></Field>
            <Field label="End" htmlFor="g-end"><Input id="g-end" type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></Field></>}
        </form>
      </Card>
      {list.isLoading ? <LoadingBlock /> : list.isError ? <ErrorState message={errMsg(list.error)} onRetry={() => list.refetch()} /> : !list.data?.length ? <Card><EmptyState title="No goals yet" text="Create a daily, weekly, monthly or custom target above." /></Card> : (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card><h2 className="font-semibold">Active</h2><ul className="divide-y divide-line">{list.data.filter((g) => g.active).map((g) => <GoalRow key={g.id} g={g} onDelete={() => remove.mutate(g.id)} />)}</ul>{!list.data.some((g) => g.active) && <p className="py-3 text-sm text-muted">No active goals.</p>}</Card>
          <Card><h2 className="font-semibold">History</h2><ul className="divide-y divide-line">{list.data.filter((g) => !g.active).map((g) => <GoalRow key={g.id} g={g} onDelete={() => remove.mutate(g.id)} />)}</ul>{!list.data.some((g) => !g.active) && <p className="py-3 text-sm text-muted">Finished goals will appear here.</p>}</Card>
        </div>)}
    </>
  );
}
