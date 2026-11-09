import { createContext, useContext, useState, type ReactNode } from "react";

// Two languages, one flat dictionary each. Keys are checked by TypeScript: a key missing in
// Spanish is a compile error.
const en = {
  "nav.dashboard": "Dashboard",
  "nav.promoters": "Promoters",
  "nav.leads": "Leads",
  "nav.users": "Users",
  "nav.logout": "Log out",
  "login.title": "Sign in",
  "login.email": "E-mail",
  "login.password": "Password",
  "login.submit": "Sign in",
  "login.demo": "Demo account",
  "period.today": "Today",
  "period.week": "This week",
  "period.month": "This month",
  "period.all": "All time",
  "dash.total": "Leads",
  "dash.synced": "Synced to CRM",
  "dash.pending": "Pending sync",
  "dash.failed": "Failed",
  "dash.unattributed": "Unattributed",
  "dash.leaderboard": "Leaderboard",
  "dash.rank": "#",
  "dash.promoter": "Promoter",
  "dash.leads": "Leads",
  "dash.empty": "No promoters yet.",
  "prom.new": "New promoter",
  "prom.name": "Name",
  "prom.email": "E-mail (optional)",
  "prom.link": "Referral link",
  "prom.copy": "Copy",
  "prom.copied": "Copied",
  "prom.edit": "Edit",
  "prom.save": "Save",
  "prom.cancel": "Cancel",
  "prom.archive": "Archive",
  "prom.unarchive": "Restore",
  "prom.showArchived": "Show archived",
  "prom.archived": "Archived",
  "leads.search": "Search name or e-mail",
  "leads.allStatuses": "All statuses",
  "leads.name": "Name",
  "leads.promoter": "Promoter",
  "leads.status": "CRM",
  "leads.date": "Date",
  "leads.retry": "Retry",
  "leads.none": "No leads match.",
  "leads.prev": "Previous",
  "leads.next": "Next",
  "status.pending": "pending",
  "status.synced": "synced",
  "status.failed": "failed",
  "users.new": "New user",
  "users.name": "Name",
  "users.email": "E-mail",
  "users.password": "Password (min. 10)",
  "users.role": "Role",
  "users.admin": "Admin",
  "users.collaborator": "Collaborator",
  "users.active": "Active",
  "users.deactivate": "Deactivate",
  "users.activate": "Activate",
  "users.create": "Create",
  "join.title": "Sign up",
  "join.referredBy": "Referred by",
  "join.firstName": "First name",
  "join.lastName": "Last name",
  "join.email": "E-mail",
  "join.phone": "Phone (optional)",
  "join.submit": "Send",
  "join.thanks": "Thank you! We will contact you soon.",
  "join.another": "Register someone else",
  "common.loading": "Loading…",
  "common.error": "Something went wrong.",
  "common.notFound": "Page not found.",
} as const;

type Key = keyof typeof en;

const es: Record<Key, string> = {
  "nav.dashboard": "Panel",
  "nav.promoters": "Promotores",
  "nav.leads": "Leads",
  "nav.users": "Usuarios",
  "nav.logout": "Salir",
  "login.title": "Iniciar sesión",
  "login.email": "Correo",
  "login.password": "Contraseña",
  "login.submit": "Entrar",
  "login.demo": "Cuenta demo",
  "period.today": "Hoy",
  "period.week": "Esta semana",
  "period.month": "Este mes",
  "period.all": "Todo",
  "dash.total": "Leads",
  "dash.synced": "En el CRM",
  "dash.pending": "Pendientes",
  "dash.failed": "Fallidos",
  "dash.unattributed": "Sin promotor",
  "dash.leaderboard": "Ranking",
  "dash.rank": "#",
  "dash.promoter": "Promotor",
  "dash.leads": "Leads",
  "dash.empty": "Aún no hay promotores.",
  "prom.new": "Nuevo promotor",
  "prom.name": "Nombre",
  "prom.email": "Correo (opcional)",
  "prom.link": "Link de referido",
  "prom.copy": "Copiar",
  "prom.copied": "Copiado",
  "prom.edit": "Editar",
  "prom.save": "Guardar",
  "prom.cancel": "Cancelar",
  "prom.archive": "Archivar",
  "prom.unarchive": "Restaurar",
  "prom.showArchived": "Ver archivados",
  "prom.archived": "Archivado",
  "leads.search": "Buscar nombre o correo",
  "leads.allStatuses": "Todos los estados",
  "leads.name": "Nombre",
  "leads.promoter": "Promotor",
  "leads.status": "CRM",
  "leads.date": "Fecha",
  "leads.retry": "Reintentar",
  "leads.none": "No hay leads.",
  "leads.prev": "Anterior",
  "leads.next": "Siguiente",
  "status.pending": "pendiente",
  "status.synced": "sincronizado",
  "status.failed": "fallido",
  "users.new": "Nuevo usuario",
  "users.name": "Nombre",
  "users.email": "Correo",
  "users.password": "Contraseña (mín. 10)",
  "users.role": "Rol",
  "users.admin": "Admin",
  "users.collaborator": "Colaborador",
  "users.active": "Activo",
  "users.deactivate": "Desactivar",
  "users.activate": "Activar",
  "users.create": "Crear",
  "join.title": "Regístrate",
  "join.referredBy": "Referido por",
  "join.firstName": "Nombre",
  "join.lastName": "Apellido",
  "join.email": "Correo",
  "join.phone": "Teléfono (opcional)",
  "join.submit": "Enviar",
  "join.thanks": "¡Gracias! Te contactaremos pronto.",
  "join.another": "Registrar a otra persona",
  "common.loading": "Cargando…",
  "common.error": "Algo salió mal.",
  "common.notFound": "Página no encontrada.",
};

export type Lang = "en" | "es";
const dictionaries: Record<Lang, Record<Key, string>> = { en, es };

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem("nexus.lang");
    if (saved === "en" || saved === "es") return saved;
  } catch {
    /* storage blocked: fall back to the browser language */
  }
  return navigator.language.toLowerCase().startsWith("es") ? "es" : "en";
}

interface I18n {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: Key) => string;
}

const I18nContext = createContext<I18n | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);
  const setLang = (l: Lang) => {
    setLangState(l);
    document.documentElement.lang = l;
    try {
      localStorage.setItem("nexus.lang", l);
    } catch {
      /* ignore */
    }
  };
  const t = (key: Key) => dictionaries[lang][key];
  return <I18nContext.Provider value={{ lang, setLang, t }}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n outside I18nProvider");
  return ctx;
}
