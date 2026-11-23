import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { analyticsApi } from "../api";
import { errMsg } from "../api/client";
import { Card, EmptyState, ErrorState, LoadingBlock, PageHeader } from "../components/ui";

const grid = <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />;
const axis = { stroke: "var(--muted)", fontSize: 12 };

function Chart({ title, height = 260, children }: { title: string; height?: number; children: React.ReactNode }) {
  return <Card><h2 className="mb-3 font-semibold">{title}</h2><div style={{ height }}><ResponsiveContainer width="100%" height="100%">{children as React.ReactElement}</ResponsiveContainer></div></Card>;
}

export default function Analytics() {
  const overview = useQuery({ queryKey: ["analytics", "overview"], queryFn: analyticsApi.overview });
  const diff = useQuery({ queryKey: ["analytics", "difficulty"], queryFn: analyticsApi.difficulty });
  const topics = useQuery({ queryKey: ["analytics", "topics"], queryFn: analyticsApi.topics });
  const weekly = useQuery({ queryKey: ["analytics", "weekly"], queryFn: () => analyticsApi.activity("week", 12) });
  const monthly = useQuery({ queryKey: ["analytics", "monthly"], queryFn: () => analyticsApi.activity("month", 6) });

  if (overview.isLoading) return <LoadingBlock rows={5} />;
  if (overview.isError || !overview.data) return <ErrorState message={errMsg(overview.error)} onRetry={() => overview.refetch()} />;
  const o = overview.data;
  if (o.total_problems === 0) return <><PageHeader title="Analytics" /><Card><EmptyState title="Nothing to analyze yet" text="Add some problems and your charts will appear here." /></Card></>;
  const rev = o.revisions as { completed: number; pending: number; overdue: number; skipped: number; completion_rate: number | null };
  const revData = [{ name: "Completed", value: rev.completed, c: "var(--easy)" }, { name: "Pending", value: rev.pending - rev.overdue, c: "var(--accent)" }, { name: "Overdue", value: rev.overdue, c: "var(--hard)" }, { name: "Skipped", value: rev.skipped, c: "var(--muted)" }].filter((d) => d.value > 0);
  const topicData = (topics.data ?? []).filter((t) => t.total > 0).map((t) => ({ name: t.name, solve_rate: t.solve_rate ?? 0, total: t.total }));

  return (
    <>
      <PageHeader title="Analytics" subtitle="Calculated from your tracked problems and activity." />
      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Card><p className="text-xs uppercase text-muted">Avg. confidence</p><p className="text-2xl font-semibold">{o.avg_confidence ?? "N/A"}</p></Card>
        <Card><p className="text-xs uppercase text-muted">Avg. time per solve</p><p className="text-2xl font-semibold">{o.avg_time_minutes != null ? `${o.avg_time_minutes} min` : "N/A"}</p></Card>
        <Card><p className="text-xs uppercase text-muted">Consistency (30 days)</p><p className="text-2xl font-semibold">{o.consistency_30d.percent}%</p><p className="text-xs text-muted">{o.consistency_30d.active_days} active days</p></Card>
        <Card><p className="text-xs uppercase text-muted">Revision completion</p><p className="text-2xl font-semibold">{rev.completion_rate != null ? `${rev.completion_rate}%` : "N/A"}</p></Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Chart title="Difficulty distribution">
          <BarChart data={diff.data ?? []}>{grid}<XAxis dataKey="difficulty" {...axis} /><YAxis allowDecimals={false} {...axis} /><Tooltip /><Legend /><Bar dataKey="total" name="Tracked" fill="var(--muted)" /><Bar dataKey="solved" name="Solved" fill="var(--accent)" /></BarChart>
        </Chart>
        <Chart title="Topic performance (solve rate %)">
          {topicData.length ? <BarChart data={topicData} layout="vertical" margin={{ left: 40 }}>{grid}<XAxis type="number" domain={[0, 100]} {...axis} /><YAxis type="category" dataKey="name" width={110} {...axis} /><Tooltip /><Bar dataKey="solve_rate" name="Solve rate %" fill="var(--accent)" /></BarChart> : <BarChart data={[]} />}
        </Chart>
        <Chart title="Solving trend (12 weeks)">
          <LineChart data={weekly.data ?? []}>{grid}<XAxis dataKey="period" {...axis} /><YAxis allowDecimals={false} {...axis} /><Tooltip /><Legend /><Line type="monotone" dataKey="solved" name="Solved" stroke="var(--easy)" strokeWidth={2} /><Line type="monotone" dataKey="attempts" name="Attempts" stroke="var(--accent)" strokeWidth={2} /></LineChart>
        </Chart>
        <Chart title="Monthly activity">
          <BarChart data={monthly.data ?? []}>{grid}<XAxis dataKey="period" {...axis} /><YAxis allowDecimals={false} {...axis} /><Tooltip /><Legend /><Bar dataKey="solved" name="Solved" fill="var(--easy)" /><Bar dataKey="active_days" name="Active days" fill="var(--accent)" /></BarChart>
        </Chart>
        <Chart title="Revision performance">
          {revData.length ? <PieChart><Pie data={revData} dataKey="value" nameKey="name" outerRadius={90} label>{revData.map((d) => <Cell key={d.name} fill={d.c} />)}</Pie><Tooltip /><Legend /></PieChart> : <PieChart />}
        </Chart>
        <Chart title="Weekly consistency (active days / week)">
          <BarChart data={weekly.data ?? []}>{grid}<XAxis dataKey="period" {...axis} /><YAxis allowDecimals={false} domain={[0, 7]} {...axis} /><Tooltip /><Bar dataKey="active_days" name="Active days" fill="var(--accent)" /></BarChart>
        </Chart>
      </div>
    </>
  );
}
