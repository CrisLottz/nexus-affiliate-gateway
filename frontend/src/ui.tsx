import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import type { CrmStatus } from "./api";
import { useI18n } from "./i18n";

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const styles = {
    primary: "bg-brand text-white hover:opacity-90",
    ghost: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100",
    danger: "border border-red-200 bg-white text-red-700 hover:bg-red-50",
  }[variant];
  return (
    <button
      className={`rounded-md px-3 py-1.5 text-sm font-medium transition disabled:opacity-50 ${styles} ${className}`}
      {...props}
    />
  );
}

export function Field({
  label,
  error,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      <input
        className={`w-full rounded-md border bg-white px-3 py-2 outline-none focus:ring-2 focus:ring-brand/40 ${
          error ? "border-red-400" : "border-slate-300"
        }`}
        {...props}
      />
      {error && <span className="mt-1 block text-xs text-red-600">{error}</span>}
    </label>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-lg border border-slate-200 bg-white p-4 shadow-sm ${className}`}>{children}</div>;
}

export function StatusBadge({ status }: { status: CrmStatus }) {
  const { t } = useI18n();
  const color = {
    synced: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    pending: "bg-amber-50 text-amber-700 ring-amber-200",
    failed: "bg-red-50 text-red-700 ring-red-200",
  }[status];
  return <span className={`rounded-full px-2 py-0.5 text-xs ring-1 ${color}`}>{t(`status.${status}`)}</span>;
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{message}</p>;
}

export function formatDate(iso: string, lang: string) {
  return new Date(iso).toLocaleString(lang === "es" ? "es-NI" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
