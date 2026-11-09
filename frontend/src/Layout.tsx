import { NavLink, Outlet } from "react-router-dom";
import { useApp } from "./app-context";
import { useI18n } from "./i18n";

export function Brand() {
  const { config } = useApp();
  if (!config) return null;
  return (
    <span className="flex items-center gap-2 font-semibold">
      {config.brand_logo_url ? (
        <img src={config.brand_logo_url} alt="" className="h-7 w-7 rounded" />
      ) : (
        <span className="grid h-7 w-7 place-items-center rounded bg-brand text-sm text-white">
          {config.brand_name.slice(0, 1)}
        </span>
      )}
      {config.brand_name}
    </span>
  );
}

export function LangSwitch() {
  const { lang, setLang } = useI18n();
  return (
    <button
      className="rounded border border-slate-300 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100"
      onClick={() => setLang(lang === "en" ? "es" : "en")}
      aria-label="Change language"
    >
      {lang === "en" ? "ES" : "EN"}
    </button>
  );
}

export function Layout() {
  const { user, logout } = useApp();
  const { t } = useI18n();
  const link = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-1.5 text-sm ${isActive ? "bg-brand/10 font-medium text-brand" : "text-slate-600 hover:bg-slate-100"}`;

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-3">
          <Brand />
          <nav className="ml-4 flex flex-wrap gap-1">
            <NavLink to="/" end className={link}>{t("nav.dashboard")}</NavLink>
            <NavLink to="/promoters" className={link}>{t("nav.promoters")}</NavLink>
            <NavLink to="/leads" className={link}>{t("nav.leads")}</NavLink>
            {user?.role === "admin" && <NavLink to="/users" className={link}>{t("nav.users")}</NavLink>}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm text-slate-600">
            <LangSwitch />
            <span className="hidden sm:inline">{user?.name}</span>
            <button className="text-slate-500 hover:text-slate-900" onClick={() => logout()}>
              {t("nav.logout")}
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
