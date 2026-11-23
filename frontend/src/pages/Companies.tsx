import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Building2, Info } from "lucide-react";
import { topicApi } from "../api";
import { errMsg } from "../api/client";
import { Card, ErrorState, LoadingBlock, PageHeader, ProgressBar } from "../components/ui";

export default function Companies() {
  const q = useQuery({ queryKey: ["companies"], queryFn: topicApi.companies });
  return (
    <>
      <PageHeader title="Interview preparation" subtitle="Organize problems by the company you're preparing for." />
      <Card className="mb-4 flex gap-2 text-sm text-muted"><Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /><p>Company tags are labels <strong className="text-fg">you</strong> apply to your own problems (from the problem form). CodeTrack does not ship or claim any official company question lists.</p></Card>
      {q.isLoading ? <LoadingBlock rows={4} /> : q.isError ? <ErrorState message={errMsg(q.error)} onRetry={() => q.refetch()} /> : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {q.data?.map((c) => (
            <Link key={c.id} to={`/problems?company_id=${c.id}`} aria-label={`${c.name}: ${c.solved} of ${c.total} solved`}>
              <Card className="h-full transition hover:border-accent"><div className="mb-3 flex items-center gap-2 font-medium"><Building2 className="h-4 w-4 text-accent" />{c.name}</div>
                <ProgressBar value={c.solved} max={c.total} label={`${c.name} progress`} /><p className="mt-2 text-xs text-muted">{c.total === 0 ? "No tagged problems" : `${c.solved} of ${c.total} solved`}</p></Card>
            </Link>))}
        </div>)}
    </>
  );
}
