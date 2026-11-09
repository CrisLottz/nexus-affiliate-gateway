import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type Role, type User } from "../api";
import { useApp } from "../app-context";
import { useI18n } from "../i18n";
import { Button, Card, ErrorNote, Field } from "../ui";

const empty = { name: "", email: "", password: "", role: "collaborator" as Role };

export function UsersPage() {
  const { user: me } = useApp();
  const { t } = useI18n();
  const [users, setUsers] = useState<User[]>([]);
  const [form, setForm] = useState(empty);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api<{ users: User[] }>("/api/users").then((r) => setUsers(r.users)).catch(() => setError(t("common.error")));
  }, [t]);
  useEffect(load, [load]);

  const handle = (err: unknown) => {
    if (err instanceof ApiError && err.status === 422) setFields(err.fields);
    else setError(err instanceof ApiError ? err.message : t("common.error"));
  };

  async function create(e: FormEvent) {
    e.preventDefault();
    setFields({});
    setError(null);
    try {
      await api("/api/users", { method: "POST", body: form });
      setForm(empty);
      load();
    } catch (err) {
      handle(err);
    }
  }

  const patch = (id: number, body: Partial<User>) =>
    api(`/api/users/${id}`, { method: "PATCH", body }).then(load).catch(handle);

  return (
    <div className="space-y-4">
      <Card>
        <form onSubmit={create} className="grid items-end gap-3 md:grid-cols-[1fr_1fr_1fr_auto_auto]">
          <Field label={t("users.name")} required value={form.name} error={fields.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Field label={t("users.email")} type="email" required value={form.email} error={fields.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <Field label={t("users.password")} type="password" required minLength={10} value={form.password}
            error={fields.password} autoComplete="new-password"
            onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">{t("users.role")}</span>
            <select className="rounded-md border border-slate-300 bg-white px-3 py-2" value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
              <option value="collaborator">{t("users.collaborator")}</option>
              <option value="admin">{t("users.admin")}</option>
            </select>
          </label>
          <Button type="submit">{t("users.create")}</Button>
        </form>
      </Card>
      <ErrorNote message={error} />
      <Card className="p-0">
        <ul>
          {users.map((u) => (
            <li key={u.id} className={`flex flex-wrap items-center gap-3 border-b border-slate-100 px-4 py-3 last:border-0 ${u.is_active ? "" : "opacity-60"}`}>
              <div className="min-w-0 flex-1">
                <p className="font-medium">{u.name}</p>
                <p className="text-xs text-slate-500">{u.email}</p>
              </div>
              <select className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm" value={u.role}
                disabled={u.id === me?.id} onChange={(e) => patch(u.id, { role: e.target.value as Role })}>
                <option value="collaborator">{t("users.collaborator")}</option>
                <option value="admin">{t("users.admin")}</option>
              </select>
              {u.id !== me?.id && (
                <Button variant={u.is_active ? "danger" : "ghost"} onClick={() => patch(u.id, { is_active: !u.is_active })}>
                  {u.is_active ? t("users.deactivate") : t("users.activate")}
                </Button>
              )}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
