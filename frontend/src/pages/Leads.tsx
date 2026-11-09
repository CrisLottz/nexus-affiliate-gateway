import { useCallback, useEffect, useState } from "react";
import { api, type CrmStatus, type Lead } from "../api";
import { useApp } from "../app-context";
import { useI18n } from "../i18n";
import { Button, Card, ErrorNote, formatDate, StatusBadge } from "../ui";

interface Page {
  leads: Lead[];
  page: number;
  page_size: number;
  total: number;
}

export function LeadsPage() {
  const { user } = useApp();
  const { t, lang } = useI18n();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<"" | CrmStatus>("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    const params = new URLSearchParams({ page: String(page) });
    if (q.trim()) params.set("q", q.trim());
    if (status) params.set("crm_status", status);
    api<Page>(`/api/leads?${params}`)
      .then(setData)
      .catch(() => setError(t("common.error")));
  }, [page, q, status, t]);

  useEffect(() => {
    const id = setTimeout(load, 250); // debounce typing in the search box
    return () => clearTimeout(id);
  }, [load]);

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <input className="min-w-60 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          placeholder={t("leads.search")} value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <select className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm" value={status}
          onChange={(e) => { setStatus(e.target.value as "" | CrmStatus); setPage(1); }}>
          <option value="">{t("leads.allStatuses")}</option>
          {(["pending", "synced", "failed"] as const).map((s) => <option key={s} value={s}>{t(`status.${s}`)}</option>)}
        </select>
      </div>
      <ErrorNote message={error} />
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">{t("leads.name")}</th>
              <th className="px-4 py-2">{t("leads.promoter")}</th>
              <th className="px-4 py-2">{t("leads.status")}</th>
              <th className="px-4 py-2">{t("leads.date")}</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {data?.leads.map((l) => (
              <tr key={l.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-2">
                  <p className="font-medium">{l.first_name} {l.last_name}</p>
                  <p className="text-xs text-slate-500">{l.email}{l.phone ? ` · ${l.phone}` : ""}</p>
                </td>
                <td className="px-4 py-2">{l.promoter?.name ?? <span className="text-slate-400">—</span>}</td>
                <td className="px-4 py-2"><StatusBadge status={l.crm_status} /></td>
                <td className="whitespace-nowrap px-4 py-2 text-slate-500">{formatDate(l.created_at, lang)}</td>
                <td className="px-4 py-2 text-right">
                  {user?.role === "admin" && l.crm_status !== "synced" && (
                    <Button variant="ghost" onClick={() => api(`/api/leads/${l.id}/retry`, { method: "POST" }).then(load)}>
                      {t("leads.retry")}
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.leads.length === 0 && <p className="p-4 text-sm text-slate-500">{t("leads.none")}</p>}
      </Card>
      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>{data?.total ?? 0} leads</span>
        <div className="flex items-center gap-2">
          <Button variant="ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>{t("leads.prev")}</Button>
          <span className="tabular-nums">{page} / {pages}</span>
          <Button variant="ghost" disabled={page >= pages} onClick={() => setPage(page + 1)}>{t("leads.next")}</Button>
        </div>
      </div>
    </div>
  );
}
