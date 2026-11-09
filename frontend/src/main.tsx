import { StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppProvider, useApp } from "./app-context";
import { I18nProvider, useI18n } from "./i18n";
import "./index.css";
import { Layout } from "./Layout";
import { DashboardPage } from "./pages/Dashboard";
import { JoinPage } from "./pages/Join";
import { LeadsPage } from "./pages/Leads";
import { LoginPage } from "./pages/Login";
import { PromotersPage } from "./pages/Promoters";
import { UsersPage } from "./pages/Users";

function RequireUser({ children, admin = false }: { children: ReactNode; admin?: boolean }) {
  const { user } = useApp();
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}

function App() {
  const { ready, user } = useApp();
  const { t } = useI18n();
  if (!ready) return <p className="p-8 text-slate-500">{t("common.loading")}</p>;
  return (
    <Routes>
      <Route path="/join" element={<JoinPage />} />
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route
        element={
          <RequireUser>
            <Layout />
          </RequireUser>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="promoters" element={<PromotersPage />} />
        <Route path="leads" element={<LeadsPage />} />
        <Route
          path="users"
          element={
            <RequireUser admin>
              <UsersPage />
            </RequireUser>
          }
        />
      </Route>
      <Route path="*" element={<p className="p-8">{t("common.notFound")}</p>} />
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <I18nProvider>
      <AppProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AppProvider>
    </I18nProvider>
  </StrictMode>,
);
