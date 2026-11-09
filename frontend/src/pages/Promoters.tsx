import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type Promoter } from "../api";
import { useApp } from "../app-context";
import { useI18n } from "../i18n";
import { Button, Card, ErrorNote, Field } from "../ui";

function referralLink(p: Promoter) {
  return `${window.location.origin}/join?ref=${p.public_id}`;
}

function CopyButton({ text }: { text: string }) {
  const { t } = useI18n();
  const [done, setDone] = useState(false);
  return (
    <Button variant="ghost" onClick={async () => {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    }}>
      {done ? t("prom.copied") : t("prom.copy")}
    </Button>
  );
}

export function PromotersPage() {
  const { user } = useApp();
  const { t } = useI18n();
  const isAdmin = user?.role === "admin";
  const [promoters, setPromoters] = useState<Promoter[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [form, setForm] = useState({ name: "", email: "" });
  const [editing, setEditing] = useState<{ id: number; name: string; email: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api<{ promoters: Promoter[] }>(`/api/promoters${showArchived ? "?include_archived=1" : ""}`)
      .then((r) => setPromoters(r.promoters))
      .catch(() => setError(t("common.error")));
  }, [showArchived, t]);

  useEffect(load, [load]);

  const run = async (fn: () => Promise<unknown>) => {
    setError(null);
    try {
      await fn();
      load();
    } catch (err) {
      setError(err instanceof ApiError ? Object.values(err.fields)[0] ?? err.message : t("common.error"));
    }
  };

  async function create(e: FormEvent) {
    e.preventDefault();
    await run(() => api("/api/promoters", { method: "POST", body: { name: form.name, email: form.email || null } }));
    setForm({ name: "", email: "" });
  }

  return (
    <div className="space-y-4">
      {isAdmin && (
        <Card>
          <form onSubmit={create} className="grid items-end gap-3 sm:grid-cols-[1fr_1fr_auto]">
            <Field label={t("prom.name")} required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Field label={t("prom.email")} type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <Button type="submit">{t("prom.new")}</Button>
          </form>
        </Card>
      )}
      <ErrorNote message={error} />
      <label className="flex items-center gap-2 text-sm text-slate-600">
        <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
        {t("prom.showArchived")}
      </label>
      <div className="space-y-2">
        {promoters.map((p) => (
          <Card key={p.id} className={p.archived ? "opacity-60" : ""}>
            {editing?.id === p.id ? (
              <div className="grid items-end gap-3 sm:grid-cols-[1fr_1fr_auto_auto]">
                <Field label={t("prom.name")} value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
                <Field label={t("prom.email")} type="email" value={editing.email} onChange={(e) => setEditing({ ...editing, email: e.target.value })} />
                <Button onClick={() => run(async () => {
                  await api(`/api/promoters/${p.id}`, { method: "PATCH", body: { name: editing.name, email: editing.email || null } });
                  setEditing(null);
                })}>{t("prom.save")}</Button>
                <Button variant="ghost" onClick={() => setEditing(null)}>{t("prom.cancel")}</Button>
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-3">
                <div className="min-w-0 flex-1">
                  <p className="font-medium">
                    {p.name} {p.archived && <span className="ml-1 text-xs text-slate-500">({t("prom.archived")})</span>}
                  </p>
                  <p className="truncate font-mono text-xs text-slate-500">{referralLink(p)}</p>
                </div>
                <CopyButton text={referralLink(p)} />
                {isAdmin && (
                  <>
                    <Button variant="ghost" onClick={() => setEditing({ id: p.id, name: p.name, email: p.email ?? "" })}>{t("prom.edit")}</Button>
                    {p.archived ? (
                      <Button variant="ghost" onClick={() => run(() => api(`/api/promoters/${p.id}/unarchive`, { method: "POST" }))}>{t("prom.unarchive")}</Button>
                    ) : (
                      <Button variant="danger" onClick={() => run(() => api(`/api/promoters/${p.id}/archive`, { method: "POST" }))}>{t("prom.archive")}</Button>
                    )}
                  </>
                )}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
