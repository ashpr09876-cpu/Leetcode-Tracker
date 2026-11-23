import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { CheckCircle2, XCircle, X } from "lucide-react";

interface T { id: number; kind: "success" | "error"; text: string }
interface Ctx { success: (m: string) => void; error: (m: string) => void }
const ToastCtx = createContext<Ctx | null>(null);
let seq = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<T[]>([]);
  const dismiss = (id: number) => setItems((l) => l.filter((x) => x.id !== id));
  const push = useCallback((kind: T["kind"], text: string) => {
    const id = ++seq;
    setItems((l) => [...l, { id, kind, text }]);
    setTimeout(() => dismiss(id), kind === "error" ? 7000 : 3500);
  }, []);
  const value: Ctx = { success: (m) => push("success", m), error: (m) => push("error", m) };
  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2" role="region" aria-live="polite" aria-label="Notifications">
        {items.map((t) => (
          <div key={t.id} role={t.kind === "error" ? "alert" : "status"} className="flex items-start gap-2 rounded-lg border border-line bg-card p-3 text-sm shadow-lg">
            {t.kind === "success" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-easy" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-hard" />}
            <span className="flex-1">{t.text}</span>
            <button aria-label="Dismiss notification" onClick={() => dismiss(t.id)} className="text-muted hover:text-fg"><X className="h-4 w-4" /></button>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
export function useToast() {
  const c = useContext(ToastCtx);
  if (!c) throw new Error("useToast must be used inside ToastProvider");
  return c;
}
