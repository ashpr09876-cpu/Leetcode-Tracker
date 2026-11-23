import type { ActivityDay } from "../types";

/** GitHub-style heatmap. Dates are plain YYYY-MM-DD strings already bucketed in the user's timezone by the server. */
export default function Heatmap({ start, days, items }: { start: string; days: number; items: ActivityDay[] }) {
  const map = new Map(items.map((i) => [i.date, i.solved + i.attempts]));
  const first = new Date(start + "T00:00:00Z");
  const cells: { date: string; n: number; col: number; row: number }[] = [];
  const offset = first.getUTCDay();
  for (let i = 0; i < days; i++) {
    const d = new Date(first.getTime() + i * 86400000);
    const iso = d.toISOString().slice(0, 10);
    cells.push({ date: iso, n: map.get(iso) ?? 0, col: Math.floor((i + offset) / 7), row: (i + offset) % 7 });
  }
  const level = (n: number) => (n === 0 ? 0 : n < 2 ? 1 : n < 4 ? 2 : n < 7 ? 3 : 4);
  const cols = Math.max(...cells.map((c) => c.col)) + 1;
  return (
    <div className="overflow-x-auto" role="img" aria-label={`Activity heatmap for the last ${days} days`}>
      <div className="grid gap-[3px]" style={{ gridTemplateColumns: `repeat(${cols}, 12px)`, gridTemplateRows: "repeat(7, 12px)", gridAutoFlow: "column" }}>
        {Array.from({ length: offset }, (_, i) => <div key={`p${i}`} />)}
        {cells.map((c) => (
          <div key={c.date} title={`${c.date}: ${c.n} ${c.n === 1 ? "activity" : "activities"}`} data-level={level(c.n)}
            className="h-3 w-3 rounded-[3px]"
            style={{ background: level(c.n) === 0 ? "var(--hover)" : `color-mix(in srgb, var(--accent) ${[0, 30, 55, 80, 100][level(c.n)]}%, transparent)` }} />
        ))}
      </div>
    </div>
  );
}
