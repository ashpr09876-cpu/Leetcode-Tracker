import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bookmark, CalendarPlus, ExternalLink, Pencil, Trash2 } from "lucide-react";
import { problemApi } from "../api";
import { errMsg } from "../api/client";
import { useToast } from "../contexts/ToastContext";
import ProblemForm from "../components/ProblemForm";
import { Badge, Button, Card, ConfirmDialog, ErrorState, LoadingBlock, Modal, PageHeader, Textarea } from "../components/ui";
import { diffColor, fmtDate, fmtDateTime } from "../utils/format";
import { STATUS_LABEL } from "../types";

export default function ProblemDetail() {
  const id = Number(useParams().id);
  const nav = useNavigate();
  const toast = useToast();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [note, setNote] = useState("");
  const q = useQuery({ queryKey: ["problem", id], queryFn: () => problemApi.get(id) });
  const refresh = () => { qc.invalidateQueries({ queryKey: ["problem", id] }); for (const k of ["problems", "dashboard", "revisions"]) qc.invalidateQueries({ queryKey: [k] }); };
  const onError = (e: unknown) => toast.error(errMsg(e));
  const bookmark = useMutation({ mutationFn: () => problemApi.bookmark(id), onSuccess: refresh, onError });
  const addNote = useMutation({ mutationFn: () => problemApi.addNote(id, note.trim()), onSuccess: () => { setNote(""); toast.success("Note added"); refresh(); }, onError });
  const delNote = useMutation({ mutationFn: (nid: number) => problemApi.removeNote(id, nid), onSuccess: refresh, onError });
  const revise = useMutation({ mutationFn: () => problemApi.scheduleRevision(id), onSuccess: (r) => { toast.success(`Revision scheduled for ${fmtDate(r.due_date)}`); refresh(); }, onError });
  const del = useMutation({ mutationFn: () => problemApi.remove(id), onSuccess: () => { toast.success("Problem deleted"); for (const k of ["problems", "dashboard", "analytics"]) qc.invalidateQueries({ queryKey: [k] }); nav("/problems"); }, onError });

  if (q.isLoading) return <LoadingBlock rows={4} />;
  if (q.isError || !q.data) return <ErrorState message={errMsg(q.error)} onRetry={() => q.refetch()} />;
  const p = q.data;
  return (
    <>
      <Link to="/problems" className="mb-2 inline-block text-sm text-accent hover:underline">&larr; All problems</Link>
      <PageHeader title={`${p.leetcode_number ? p.leetcode_number + ". " : ""}${p.title}`}
        subtitle={`Added ${fmtDate(p.created_at)}${p.source !== "manual" ? ` - source: ${p.source}` : ""}`}
        actions={<>
          <Button variant="secondary" onClick={() => bookmark.mutate()} aria-pressed={p.bookmarked}><Bookmark className={`h-4 w-4 ${p.bookmarked ? "fill-accent text-accent" : ""}`} />{p.bookmarked ? "Bookmarked" : "Bookmark"}</Button>
          <Button variant="secondary" onClick={() => setEditing(true)}><Pencil className="h-4 w-4" />Edit</Button>
          <Button variant="danger" onClick={() => setConfirm(true)}><Trash2 className="h-4 w-4" />Delete</Button>
        </>} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="space-y-3 lg:col-span-2">
          <div className="flex flex-wrap items-center gap-2"><span className={`font-medium capitalize ${diffColor[p.difficulty]}`}>{p.difficulty}</span><Badge>{STATUS_LABEL[p.status]}</Badge>{p.topics.map((t) => <Badge key={t.id}>{t.name}</Badge>)}{p.companies.map((c) => <Badge key={c.id} className="border-accent text-accent">{c.name}</Badge>)}</div>
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div><dt className="text-muted">Attempts</dt><dd className="font-medium">{p.attempts}</dd></div>
            <div><dt className="text-muted">Time spent</dt><dd className="font-medium">{p.time_spent_minutes} min</dd></div>
            <div><dt className="text-muted">Confidence</dt><dd className="font-medium">{p.confidence}/5</dd></div>
            <div><dt className="text-muted">Solved</dt><dd className="font-medium">{fmtDate(p.solved_at)}</dd></div>
          </dl>
          <div className="flex flex-wrap gap-3 text-sm">
            {p.url && <a className="inline-flex items-center gap-1 text-accent hover:underline" href={p.url} target="_blank" rel="noopener noreferrer"><ExternalLink className="h-3.5 w-3.5" />Problem</a>}
            {p.solution_url && <a className="inline-flex items-center gap-1 text-accent hover:underline" href={p.solution_url} target="_blank" rel="noopener noreferrer"><ExternalLink className="h-3.5 w-3.5" />Solution</a>}
          </div>
          {p.solution_code && <div><h2 className="mb-1 text-sm font-semibold">Solution code</h2><pre className="overflow-x-auto rounded-lg border border-line bg-bg p-3 text-xs"><code>{p.solution_code}</code></pre></div>}
          <Button variant="secondary" loading={revise.isPending} onClick={() => revise.mutate()}><CalendarPlus className="h-4 w-4" />Schedule revision</Button>
        </Card>
        <Card>
          <h2 className="mb-3 font-semibold">Notes</h2>
          <form className="mb-3 space-y-2" onSubmit={(e) => { e.preventDefault(); if (note.trim()) addNote.mutate(); }}>
            <Textarea aria-label="New note" rows={3} placeholder="Key insight, edge case, complexity..." value={note} onChange={(e) => setNote(e.target.value)} />
            <Button type="submit" disabled={!note.trim()} loading={addNote.isPending}>Add note</Button>
          </form>
          {p.notes.length === 0 ? <p className="text-sm text-muted">No notes yet.</p> : <ul className="space-y-2">{p.notes.map((n) => (
            <li key={n.id} className="rounded-lg border border-line p-2 text-sm"><p className="whitespace-pre-wrap">{n.body}</p><div className="mt-1 flex justify-between text-xs text-muted"><span>{fmtDateTime(n.created_at)}</span><button aria-label="Delete note" className="hover:text-hard" onClick={() => delNote.mutate(n.id)}>Delete</button></div></li>))}</ul>}
        </Card>
      </div>
      <Modal open={editing} onClose={() => setEditing(false)} title="Edit problem" wide><ProblemForm problem={p} onDone={() => setEditing(false)} /></Modal>
      <ConfirmDialog open={confirm} title="Delete problem?" message="This permanently deletes the problem, its notes and revisions." loading={del.isPending} onConfirm={() => del.mutate()} onClose={() => setConfirm(false)} />
    </>
  );
}
