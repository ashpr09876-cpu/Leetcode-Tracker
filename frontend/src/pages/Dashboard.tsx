import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Flame, Sparkles, Trophy } from "lucide-react";
import { aiApi, dashApi } from "../api";
import { errMsg } from "../api/client";
import { Badge, Button, Card, EmptyState, ErrorState, PageHeader, ProgressBar, Skeleton } from "../components/ui";
import Heatmap from "../components/Heatmap";
import { diffColor, fmtDate } from "../utils/format";

function Stat({ label, value, sub, color = "" }: { label: string; value: string | number; sub?: string; color?: string }) {
  return <Card><p className="text-xs uppercase tracking-wide text-muted">{label}</p><p className={`mt-1 text-2xl font-semibold ${color}`}>{value}</p>{sub && <p className="text-xs text-muted">{sub}</p>}</Card>;
}

export default function Dashboard() {
  const summary = useQuery({ queryKey: ["dashboard", "summary"], queryFn: dashApi.summary });
  const activity = useQuery({ queryKey: ["dashboard", "activity"], queryFn: () => dashApi.activity(365) });
  const topics = useQuery({ queryKey: ["dashboard", "topics"], queryFn: dashApi.topics });
  const recent = useQuery({ queryKey: ["dashboard", "recent"], queryFn: dashApi.recent });
  const aiStatus = useQuery({ queryKey: ["ai-status"], queryFn: aiApi.status });
  const [rec, setRec] = useState<string | null>(null);
  const recommend = useMutation({ mutationFn: aiApi.recommend, onSuccess: (r) => setRec(r.reply) });

  if (summary.isLoading) return <div className="space-y-4"><Skeleton className="h-8 w-48" /><div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div><Skeleton className="h-40" /></div>;
  if (summary.isError || !summary.data) return <ErrorState message={errMsg(summary.error)} onRetry={() => summary.refetch()} />;
  const s = summary.data;
  const dist = [{ name: "Easy", value: s.easy, c: "var(--easy)" }, { name: "Medium", value: s.medium, c: "var(--medium)" }, { name: "Hard", value: s.hard, c: "var(--hard)" }];
  const goalMax = s.daily_goal || 0;

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Everything here is calculated from your own records." actions={<Link to="/problems?new=1"><Button>Add problem</Button></Link>} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Solved" value={s.total_solved} sub={`${s.total_problems} tracked`} />
        <Stat label="Easy" value={s.easy} color="text-easy" />
        <Stat label="Medium" value={s.medium} color="text-medium" />
        <Stat label="Hard" value={s.hard} color="text-hard" />
        <Stat label="Current streak" value={`${s.current_streak} d`} sub="days with any activity" />
        <Stat label="Longest streak" value={`${s.longest_streak} d`} />
        <Stat label="Acceptance rate" value={s.acceptance_rate != null ? `${s.acceptance_rate}%` : "N/A"} sub={s.acceptance_rate == null ? "Needs LeetCode sync" : "from LeetCode profile"} />
        <Stat label="Contest rating" value={s.contest_rating ?? "N/A"} sub={s.contest_rating == null ? "Needs LeetCode sync" : "from LeetCode profile"} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h2 className="mb-3 font-semibold">Activity (last year)</h2>
          {activity.isLoading ? <Skeleton className="h-28" /> : activity.isError ? <ErrorState message={errMsg(activity.error)} onRetry={() => activity.refetch()} /> :
            activity.data && <Heatmap start={activity.data.start} days={activity.data.days} items={activity.data.items} />}
          <div className="mt-3 flex flex-wrap gap-4 text-sm text-muted">
            <span>Today: {s.today.solved} solved / {s.today.attempts} attempts</span>
            <span>This week: {s.week.solved} solved / {s.week.attempts} attempts</span>
            <span>This month: {s.month.solved} solved</span>
          </div>
        </Card>
        <Card>
          <h2 className="mb-3 font-semibold">Daily goal</h2>
          {goalMax > 0 ? <><p className="mb-2 text-sm">{s.today.solved} / {goalMax} solved today</p><ProgressBar value={s.today.solved} max={goalMax} label="Daily goal progress" /></> : <p className="text-sm text-muted">No daily goal set. Set one in <Link className="text-accent hover:underline" to="/settings">Settings</Link>.</p>}
          <div className="mt-4 flex items-center gap-2 text-sm"><Flame className="h-4 w-4 text-medium" />{s.current_streak > 0 ? `${s.current_streak}-day streak` : "No active streak yet"}</div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card>
          <h2 className="mb-2 font-semibold">Difficulty distribution</h2>
          {s.total_solved === 0 ? <EmptyState title="No solved problems yet" /> : (
            <div className="h-48"><ResponsiveContainer><PieChart><Pie data={dist} dataKey="value" nameKey="name" innerRadius={45} outerRadius={70}>{dist.map((d) => <Cell key={d.name} fill={d.c} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div>)}
        </Card>
        <Card className="lg:col-span-2">
          <h2 className="mb-3 font-semibold">Topic progress</h2>
          {topics.isLoading ? <Skeleton className="h-32" /> : topics.isError ? <ErrorState message={errMsg(topics.error)} onRetry={() => topics.refetch()} /> :
            topics.data?.filter((t) => t.total > 0).length ? (
              <ul className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
                {topics.data.filter((t) => t.total > 0).slice(0, 10).map((t) => (
                  <li key={t.topic_id}><div className="mb-1 flex justify-between text-sm"><span>{t.name}</span><span className="text-muted">{t.solved}/{t.total}</span></div><ProgressBar value={t.solved} max={t.total} label={`${t.name} progress`} /></li>))}
              </ul>) : <EmptyState title="No topic data yet" text="Assign topics to problems to see progress here." />}
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="mb-3 flex items-center justify-between"><h2 className="font-semibold">Recent problems</h2><Link to="/problems" className="text-sm text-accent hover:underline">View all</Link></div>
          {recent.isLoading ? <Skeleton className="h-24" /> : recent.isError ? <ErrorState message={errMsg(recent.error)} onRetry={() => recent.refetch()} /> :
            recent.data?.length ? <ul className="divide-y divide-line">{recent.data.map((p) => (
              <li key={p.id} className="flex items-center justify-between gap-2 py-2 text-sm"><Link to={`/problems/${p.id}`} className="font-medium hover:underline">{p.title}</Link><span className="flex items-center gap-2"><span className={`capitalize ${diffColor[p.difficulty]}`}>{p.difficulty}</span><Badge>{p.status.replace("_", " ")}</Badge></span></li>))}</ul>
              : <EmptyState title="No problems yet" text="Add your first problem to start tracking." action={<Link to="/problems?new=1"><Button>Add problem</Button></Link>} />}
        </Card>
        <Card>
          <div className="mb-3 flex items-center justify-between"><h2 className="font-semibold">Upcoming revisions</h2><Link to="/revisions" className="text-sm text-accent hover:underline">Open</Link></div>
          {s.upcoming_revisions.length ? <ul className="space-y-2 text-sm">{s.upcoming_revisions.map((r) => (
            <li key={r.id} className="flex justify-between gap-2"><Link to={`/problems/${r.problem_id}`} className="truncate hover:underline">{r.problem_title}</Link><span className={r.overdue ? "text-hard" : "text-muted"}>{r.overdue ? "Overdue" : fmtDate(r.due_date)}</span></li>))}</ul>
            : <p className="text-sm text-muted">Nothing scheduled.</p>}
        </Card>
      </div>

      <Card className="mt-4">
        <h2 className="mb-2 flex items-center gap-2 font-semibold"><Sparkles className="h-4 w-4 text-accent" />AI recommendations</h2>
        {aiStatus.data && !aiStatus.data.configured ? <p className="text-sm text-muted">No AI provider is configured on this server, so there are no recommendations. See the <Link className="text-accent hover:underline" to="/ai">AI Coach page</Link> for setup steps.</p> : (
          <>
            {rec ? <p className="whitespace-pre-wrap text-sm">{rec}</p> : <p className="text-sm text-muted">Get problem suggestions based on your weakest topics.</p>}
            {recommend.isError && <p role="alert" className="mt-2 text-sm text-hard">{errMsg(recommend.error)}</p>}
            <Button className="mt-3" variant="secondary" loading={recommend.isPending} onClick={() => recommend.mutate()}><Trophy className="h-4 w-4" />Get recommendations</Button>
          </>)}
      </Card>
    </>
  );
}
