import { useEffect, useState } from "react";
import { api, type Promoter } from "../api";
import { useI18n } from "../i18n";
import { Card, ErrorNote } from "../ui";

type Period = "today" | "week" | "month" | "all";
const PERIODS: Period[] = ["today", "week", "month", "all"];

interface Summary {
  total: number;
  synced: number;
  pending: number;
  failed: number;
  unattributed: number;
}

interface Row {
  rank: number;
  promoter: Promoter;
  leads: number;
}

// The viewer's time zone decides where "today" starts.
const TZ = Intl.DateTimeFormat().resolvedOptions().timeZone;

export function DashboardPage() {
  const { t } = useI18n();
  const [period, setPeriod] = useState<Period>("month");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const qs = `period=${period}&tz=${encodeURIComponent(TZ)}`;
    Promise.all([
      api<Summary>(`/api/dashboard/summary?${qs}`),
      api<{ leaderboard: Row[] }>(`/api/dashboard/leaderboard?${qs}`),
    ])
      .then(([s, l]) => {
        setSummary(s);
        setRows(l.leaderboard);
        setError(null);
      })
      .catch(() => setError(t("common.error")));
  }, [period, t]);

  const max = Math.max(1, ...(rows ?? []).map((r) => r.leads));
  const stats: [string, number | undefined, string][] = [
    [t("dash.total"), summary?.total, "text-slate-900"],
    [t("dash.synced"), summary?.synced, "text-emerald-700"],
    [t("dash.pending"), summary?.pending, "text-amber-700"],
    [t("dash.failed"), summary?.failed, "text-red-700"],
    [t("dash.unattributed"), summary?.unattributed, "text-slate-500"],
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-1" role="tablist">
        {PERIODS.map((p) => (
          <button key={p} role="tab" aria-selected={p === period} onClick={() => setPeriod(p)}
            className={`rounded-md px-3 py-1.5 text-sm ${p === period ? "bg-brand text-white" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100"}`}>
            {t(`period.${p}`)}
          </button>
        ))}
      </div>
      <ErrorNote message={error} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {stats.map(([label, value, color]) => (
          <Card key={label}>
            <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
            <p className={`mt-1 text-2xl font-semibold tabular-nums ${color}`}>{value ?? "–"}</p>
          </Card>
        ))}
      </div>
      <Card>
        <h2 className="mb-3 font-semibold">{t("dash.leaderboard")}</h2>
        {rows && rows.length === 0 && <p className="text-sm text-slate-500">{t("dash.empty")}</p>}
        <ol className="space-y-2">
          {rows?.map((r) => (
            <li key={r.promoter.id} className="grid grid-cols-[2rem_1fr_3rem] items-center gap-3 text-sm">
              <span className="text-right font-mono text-slate-400">{r.rank}</span>
              <div>
                <div className="flex justify-between">
                  <span className={r.promoter.archived ? "text-slate-400 line-through" : ""}>{r.promoter.name}</span>
                </div>
                <div className="mt-1 h-2 rounded bg-slate-100">
                  <div className="h-2 rounded bg-brand" style={{ width: `${(r.leads / max) * 100}%` }} />
                </div>
              </div>
              <span className="text-right font-semibold tabular-nums">{r.leads}</span>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  );
}
