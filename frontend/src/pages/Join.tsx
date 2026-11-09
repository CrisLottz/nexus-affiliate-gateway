import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { useI18n } from "../i18n";
import { Brand, LangSwitch } from "../Layout";
import { Button, Card, ErrorNote, Field } from "../ui";

const empty = { first_name: "", last_name: "", email: "", phone: "", website: "" };

// Public page: /join?ref=<public_id>. The ref is read once and locked; the visitor never
// chooses a promoter.
export function JoinPage() {
  const { t } = useI18n();
  const [params] = useSearchParams();
  const ref = params.get("ref");
  const [referrer, setReferrer] = useState<string | null>(null);
  const [form, setForm] = useState(empty);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!ref) return;
    api<{ promoter: { name: string } }>(`/api/public/promoters/${encodeURIComponent(ref)}`)
      .then((r) => setReferrer(r.promoter.name))
      .catch(() => setReferrer(null)); // unknown ref: the lead is still accepted, unattributed
  }, [ref]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setFields({});
    try {
      await api("/api/public/leads", {
        method: "POST",
        body: { ...form, phone: form.phone || null, website: form.website || null, ref },
      });
      setSent(true);
      setForm(empty);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) setFields(err.fields);
      else setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  const set = (k: keyof typeof empty) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  return (
    <div className="grid min-h-screen place-items-center px-4 py-8">
      <div className="w-full max-w-md space-y-4">
        <div className="flex items-center justify-between">
          <Brand />
          <LangSwitch />
        </div>
        <Card>
          {sent ? (
            <div className="space-y-4 py-6 text-center">
              <p className="text-lg font-medium">{t("join.thanks")}</p>
              <Button variant="ghost" onClick={() => setSent(false)}>{t("join.another")}</Button>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-4" noValidate>
              <div>
                <h1 className="text-lg font-semibold">{t("join.title")}</h1>
                {referrer && (
                  <p className="text-sm text-slate-500">
                    {t("join.referredBy")} <span className="font-medium text-brand">{referrer}</span>
                  </p>
                )}
              </div>
              <ErrorNote message={error} />
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label={t("join.firstName")} required value={form.first_name}
                  onChange={set("first_name")} error={fields.first_name} />
                <Field label={t("join.lastName")} required value={form.last_name}
                  onChange={set("last_name")} error={fields.last_name} />
              </div>
              <Field label={t("join.email")} type="email" required value={form.email}
                onChange={set("email")} error={fields.email} />
              <Field label={t("join.phone")} type="tel" value={form.phone}
                onChange={set("phone")} error={fields.phone} />
              {/* Honeypot: invisible to people, tempting to bots. */}
              <input type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden="true"
                className="absolute -left-[9999px] h-0 w-0 opacity-0"
                value={form.website} onChange={set("website")} />
              <Button type="submit" disabled={busy} className="w-full">{t("join.submit")}</Button>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}
