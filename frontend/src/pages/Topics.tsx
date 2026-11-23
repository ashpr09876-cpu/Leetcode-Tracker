import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Pencil, Trash2 } from "lucide-react";
import { analyticsApi, topicApi } from "../api";
import { errMsg } from "../api/client";
import { useToast } from "../contexts/ToastContext";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Input, LoadingBlock, PageHeader, ProgressBar } from "../components/ui";
import type { TopicStat } from "../types";

export default function Topics() {
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<{ id: number; name: string } | null>(null);
  const [del, setDel] = useState<TopicStat | null>(null);
  const toast = useToast();
  const qc = useQueryClient();
  const stats = useQuery({ queryKey: ["topic-stats"], queryFn: analyticsApi.topics });
  const topics = useQuery({ queryKey: ["topics"], queryFn: topicApi.list });
  const refresh = () => { for (const k of ["topic-stats", "topics", "dashboard", "analytics"]) qc.invalidateQueries({ queryKey: [k] }); };
  const onError = (e: unknown) => toast.error(errMsg(e));
  const create = useMutation({ mutationFn: () => topicApi.create(name.trim()), onSuccess: () => { toast.success("Topic added"); setName(""); refresh(); }, onError });
  const rename = useMutation({ mutationFn: () => topicApi.rename(editing!.id, editing!.name.trim()), onSuccess: () => { setEditing(null); refresh(); }, onError });
  const remove = useMutation({ mutationFn: (id: number) => topicApi.remove(id), onSuccess: () => { toast.success("Topic deleted (problems are kept)"); setDel(null); refresh(); }, onError });
  const isDefault = (id: number) => topics.data?.find((t) => t.id === id)?.is_default;

  return (
    <>
      <PageHeader title="DSA topics" subtitle="Progress per topic. Add your own topics too." />
      <Card className="mb-4">
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (name.trim()) create.mutate(); }}>
          <Input aria-label="New topic name" placeholder="Custom topic, e.g. Segment Trees" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} />
          <Button type="submit" disabled={!name.trim()} loading={create.isPending}>Add topic</Button>
        </form>
      </Card>
      {stats.isLoading ? <LoadingBlock rows={6} /> : stats.isError ? <ErrorState message={errMsg(stats.error)} onRetry={() => stats.refetch()} /> : !stats.data?.length ? <Card><EmptyState title="No topics" /></Card> : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {stats.data.map((t) => (
            <Card key={t.topic_id}>
              <div className="mb-2 flex items-start justify-between gap-2">
                {editing?.id === t.topic_id ? (
                  <form className="flex flex-1 gap-1" onSubmit={(e) => { e.preventDefault(); rename.mutate(); }}>
                    <Input aria-label="Topic name" value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} autoFocus />
                    <Button type="submit" aria-label="Save topic name" variant="secondary"><Check className="h-4 w-4" /></Button>
                  </form>
                ) : <h2 className="font-medium">{t.name} {!isDefault(t.topic_id) && <Badge>custom</Badge>}</h2>}
                <div className="flex shrink-0"><button aria-label={`Rename ${t.name}`} className="rounded p-1 text-muted hover:bg-hover" onClick={() => setEditing({ id: t.topic_id, name: t.name })}><Pencil className="h-4 w-4" /></button>
                  <button aria-label={`Delete ${t.name}`} className="rounded p-1 text-muted hover:bg-hover hover:text-hard" onClick={() => setDel(t)}><Trash2 className="h-4 w-4" /></button></div>
              </div>
              <ProgressBar value={t.solved} max={t.total} label={`${t.name} solved`} />
              <p className="mt-2 text-xs text-muted">{t.total === 0 ? "No problems yet" : `${t.solved} of ${t.total} solved - ${t.mastered} mastered${t.avg_confidence != null ? ` - confidence ${t.avg_confidence}/5` : ""}`}</p>
            </Card>))}
        </div>)}
      <ConfirmDialog open={!!del} title="Delete topic?" message={`Removing "${del?.name}" untags it from ${del?.total ?? 0} problem(s). The problems themselves are kept.`} loading={remove.isPending} onConfirm={() => del && remove.mutate(del.topic_id)} onClose={() => setDel(null)} />
    </>
  );
}
