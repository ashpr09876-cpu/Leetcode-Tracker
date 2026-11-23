import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Send, Sparkles } from "lucide-react";
import { aiApi } from "../api";
import { errCode, errMsg } from "../api/client";
import { Button, Card, ErrorState, Input, LoadingBlock, PageHeader } from "../components/ui";

interface Msg { role: "user" | "assistant" | "error"; text: string }

export default function AICoach() {
  const status = useQuery({ queryKey: ["ai-status"], queryFn: aiApi.status });
  const qc = useQueryClient();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [conv, setConv] = useState<number | undefined>();
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const push = (m: Msg) => { setMsgs((l) => [...l, m]); setTimeout(() => endRef.current?.scrollIntoView?.({ behavior: "smooth" }), 0); };

  const run = useMutation({
    mutationFn: ({ label, fn }: { label: string; fn: () => Promise<{ conversation_id: number; reply: string }> }) => { push({ role: "user", text: label }); return fn(); },
    onSuccess: (r) => { setConv(r.conversation_id); push({ role: "assistant", text: r.reply }); qc.invalidateQueries({ queryKey: ["ai-status"] }); },
    onError: (e) => { push({ role: "error", text: errMsg(e) }); if (errCode(e) === "ai_not_configured") qc.invalidateQueries({ queryKey: ["ai-status"] }); },
  });
  const actions = [
    { label: "Analyze my performance", fn: aiApi.analyze },
    { label: "Recommend problems", fn: aiApi.recommend },
    { label: "Build my study roadmap", fn: aiApi.roadmap },
  ];

  if (status.isLoading) return <LoadingBlock />;
  if (status.isError || !status.data) return <ErrorState message={errMsg(status.error)} onRetry={() => status.refetch()} />;
  const s = status.data;

  return (
    <>
      <PageHeader title="AI Coach" subtitle={s.configured ? `Provider: ${s.active_provider} - ${s.used_today}/${s.daily_limit} requests used today` : undefined} />
      {!s.configured && (
        <Card className="mb-4 border-medium/50">
          <div className="flex gap-3"><AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-medium" aria-hidden />
            <div className="space-y-2 text-sm"><p className="font-medium">No AI provider is configured</p>
              <p className="text-muted">The coach is disabled until you add one. CodeTrack never shows made-up AI answers. Everything else works without it.</p>
              <ol className="list-decimal space-y-1 pl-5 text-muted"><li>Open <code>backend/.env</code>.</li><li>Set <code>AI_PROVIDER</code> to <code>ollama</code>, <code>gemini</code>, <code>openai</code> or <code>anthropic</code>, and fill the matching key (for Ollama: <code>OLLAMA_BASE_URL</code>).</li><li>Restart the backend, then reload this page.</li></ol>
              <p className="text-muted">Details: <code>docs/DEPLOYMENT.md</code>. You can also choose a provider in <Link to="/settings" className="text-accent hover:underline">Settings</Link>.</p></div></div>
        </Card>)}
      <Card>
        <div className="mb-3 flex flex-wrap gap-2">{actions.map((a) => <Button key={a.label} variant="secondary" disabled={!s.configured || run.isPending} onClick={() => run.mutate(a)}><Sparkles className="h-4 w-4" />{a.label}</Button>)}</div>
        <div className="mb-3 max-h-[28rem] min-h-40 space-y-3 overflow-y-auto rounded-lg border border-line bg-bg p-3" aria-live="polite">
          {msgs.length === 0 && <p className="text-sm text-muted">{s.configured ? "Ask a question or pick an analysis above. The coach sees your real statistics." : "Chat is unavailable until a provider is configured."}</p>}
          {msgs.map((m, i) => (
            <div key={i} className={m.role === "user" ? "text-right" : ""}><div className={`inline-block max-w-[90%] whitespace-pre-wrap rounded-xl px-3 py-2 text-left text-sm ${m.role === "user" ? "bg-accent text-accent-fg" : m.role === "error" ? "border border-hard/40 bg-hard/10 text-hard" : "border border-line bg-card"}`} role={m.role === "error" ? "alert" : undefined}>{m.text}</div></div>))}
          {run.isPending && <p className="text-sm text-muted">Thinking...</p>}
          <div ref={endRef} />
        </div>
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); const t = input.trim(); if (!t) return; setInput(""); run.mutate({ label: t, fn: () => aiApi.chat(t, conv) }); }}>
          <Input aria-label="Message to AI coach" placeholder="Ask about your weak topics, what to study next..." value={input} onChange={(e) => setInput(e.target.value)} disabled={!s.configured} maxLength={4000} />
          <Button type="submit" disabled={!s.configured || !input.trim() || run.isPending} aria-label="Send message"><Send className="h-4 w-4" /></Button>
        </form>
      </Card>
    </>
  );
}
