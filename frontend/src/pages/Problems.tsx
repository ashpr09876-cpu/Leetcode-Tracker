import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bookmark, Plus, Search, Trash2 } from "lucide-react";
import { problemApi, topicApi } from "../api";
import { errMsg } from "../api/client";
import { useToast } from "../contexts/ToastContext";
import { useDebounced } from "../hooks/useDebounced";
import ProblemForm from "../components/ProblemForm";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Input, LoadingBlock, Modal, PageHeader, Select } from "../components/ui";
import { diffColor } from "../utils/format";
import { STATUS_LABEL, type Problem, type Status } from "../types";

export default function Problems() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [status, setStatus] = useState("");
  const [topicId, setTopicId] = useState("");
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);
  const [adding, setAdding] = useState(params.get("new") === "1");
  const [toDelete, setToDelete] = useState<Problem | null>(null);
  const companyId = params.get("company_id");
  const dq = useDebounced(q.trim(), 300);
  const toast = useToast();
  const qc = useQueryClient();

  const topics = useQuery({ queryKey: ["topics"], queryFn: topicApi.list });
  const query = { q: dq || undefined, difficulty: difficulty || undefined, status: status || undefined, topic_id: topicId ? Number(topicId) : undefined, company_id: companyId ? Number(companyId) : undefined, sort, page, page_size: 15 };
  const list = useQuery({ queryKey: ["problems", query], queryFn: () => problemApi.list(query), placeholderData: keepPreviousData });

  const refresh = () => { for (const k of ["problems", "dashboard", "analytics", "companies", "topic-stats"]) qc.invalidateQueries({ queryKey: [k] }); };
  const bookmark = useMutation({ mutationFn: (id: number) => problemApi.bookmark(id), onSuccess: refresh, onError: (e) => toast.error(errMsg(e)) });
  const del = useMutation({ mutationFn: (id: number) => problemApi.remove(id), onSuccess: () => { toast.success("Problem deleted"); setToDelete(null); refresh(); }, onError: (e) => toast.error(errMsg(e)) });
  const reset = (fn: () => void) => { fn(); setPage(1); };
  const totalPages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.page_size)) : 1;
  const filtered = !!(dq || difficulty || status || topicId || companyId);

  return (
    <>
      <PageHeader title="Problems" subtitle={list.data ? `${list.data.total} problem${list.data.total === 1 ? "" : "s"}` : undefined} actions={<Button onClick={() => setAdding(true)}><Plus className="h-4 w-4" />Add problem</Button>} />
      <Card className="mb-4">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          <div className="relative lg:col-span-2"><Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted" aria-hidden /><Input aria-label="Search problems" placeholder="Search by title or number" className="pl-8" value={q} onChange={(e) => reset(() => setQ(e.target.value))} /></div>
          <Select aria-label="Filter by difficulty" value={difficulty} onChange={(e) => reset(() => setDifficulty(e.target.value))}><option value="">All difficulties</option><option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option></Select>
          <Select aria-label="Filter by status" value={status} onChange={(e) => reset(() => setStatus(e.target.value))}><option value="">All statuses</option>{(Object.keys(STATUS_LABEL) as Status[]).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}</Select>
          <Select aria-label="Filter by topic" value={topicId} onChange={(e) => reset(() => setTopicId(e.target.value))}><option value="">All topics</option>{topics.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</Select>
          <Select aria-label="Sort by" value={sort} onChange={(e) => reset(() => setSort(e.target.value))}><option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="title">Title</option><option value="difficulty">Difficulty</option><option value="confidence">Lowest confidence</option><option value="time">Most time spent</option></Select>
          {companyId && <Button variant="secondary" onClick={() => { params.delete("company_id"); setParams(params); setPage(1); }}>Clear company filter</Button>}
        </div>
      </Card>

      <Card className="p-0">
        {list.isLoading ? <div className="p-4"><LoadingBlock rows={5} /></div> : list.isError ? <ErrorState message={errMsg(list.error)} onRetry={() => list.refetch()} /> :
          !list.data?.items.length ? (
            filtered ? <EmptyState title="No problems match your filters" text="Try clearing a filter or searching for something else." /> :
              <EmptyState title="No problems yet" text="Add the first problem you've worked on." action={<Button onClick={() => setAdding(true)}>Add problem</Button>} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-line text-left text-xs uppercase text-muted"><tr><th className="p-3">Problem</th><th>Difficulty</th><th>Status</th><th className="hidden md:table-cell">Topics</th><th className="hidden sm:table-cell">Conf.</th><th className="p-3 text-right">Actions</th></tr></thead>
                <tbody>{list.data.items.map((p) => (
                  <tr key={p.id} className="border-b border-line last:border-0 hover:bg-hover/60">
                    <td className="p-3"><Link to={`/problems/${p.id}`} className="font-medium hover:underline">{p.leetcode_number ? `${p.leetcode_number}. ` : ""}{p.title}</Link></td>
                    <td className={`capitalize ${diffColor[p.difficulty]}`}>{p.difficulty}</td>
                    <td><Badge>{STATUS_LABEL[p.status]}</Badge></td>
                    <td className="hidden max-w-[14rem] truncate text-muted md:table-cell">{p.topics.map((t) => t.name).join(", ") || "-"}</td>
                    <td className="hidden sm:table-cell">{p.confidence}/5</td>
                    <td className="p-3 text-right whitespace-nowrap">
                      <button aria-label={p.bookmarked ? `Remove bookmark from ${p.title}` : `Bookmark ${p.title}`} aria-pressed={p.bookmarked} onClick={() => bookmark.mutate(p.id)} className="rounded p-1.5 hover:bg-hover"><Bookmark className={`h-4 w-4 ${p.bookmarked ? "fill-accent text-accent" : "text-muted"}`} /></button>
                      <button aria-label={`Delete ${p.title}`} onClick={() => setToDelete(p)} className="rounded p-1.5 text-muted hover:bg-hover hover:text-hard"><Trash2 className="h-4 w-4" /></button>
                    </td>
                  </tr>))}</tbody>
              </table>
            </div>)}
      </Card>
      {list.data && list.data.total > list.data.page_size && (
        <div className="mt-3 flex items-center justify-between text-sm">
          <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
          <span className="text-muted">Page {page} of {totalPages}</span>
          <Button variant="secondary" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</Button>
        </div>)}

      <Modal open={adding} onClose={() => { setAdding(false); if (params.get("new")) { params.delete("new"); setParams(params); } }} title="Add problem" wide><ProblemForm onDone={() => setAdding(false)} /></Modal>
      <ConfirmDialog open={!!toDelete} title="Delete problem?" message={`"${toDelete?.title}" and its notes and revisions will be permanently deleted.`} loading={del.isPending} onConfirm={() => toDelete && del.mutate(toDelete.id)} onClose={() => setToDelete(null)} />
    </>
  );
}
