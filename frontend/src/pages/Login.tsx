import { useState, type FormEvent } from "react";
import { ApiError } from "../api";
import { useApp } from "../app-context";
import { useI18n } from "../i18n";
import { Brand, LangSwitch } from "../Layout";
import { Button, Card, ErrorNote, Field } from "../ui";

export function LoginPage() {
  const { login, config } = useApp();
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  const demo = config?.demo;
  return (
    <div className="grid min-h-screen place-items-center px-4">
      <div className="w-full max-w-sm space-y-4">
        <div className="flex items-center justify-between">
          <Brand />
          <LangSwitch />
        </div>
        <Card>
          <form onSubmit={submit} className="space-y-4">
            <h1 className="text-lg font-semibold">{t("login.title")}</h1>
            <ErrorNote message={error} />
            <Field label={t("login.email")} type="email" autoComplete="username" required
              value={email} onChange={(e) => setEmail(e.target.value)} />
            <Field label={t("login.password")} type="password" autoComplete="current-password" required
              value={password} onChange={(e) => setPassword(e.target.value)} />
            <Button type="submit" disabled={busy} className="w-full">{t("login.submit")}</Button>
          </form>
        </Card>
        {demo?.enabled && demo.email && (
          <Card className="text-sm">
            <p className="font-medium">{t("login.demo")}</p>
            <p className="mt-1 font-mono text-xs text-slate-600">{demo.email} / {demo.password}</p>
            <Button variant="ghost" className="mt-2"
              onClick={() => { setEmail(demo.email!); setPassword(demo.password!); }}>
              ↳ {t("login.submit")}
            </Button>
          </Card>
        )}
      </div>
    </div>
  );
}
