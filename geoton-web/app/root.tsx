import {
  Links,
  Meta,
  NavLink,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";

import "maplibre-gl/dist/maplibre-gl.css";
import "./app.css";

function NavItem({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
    >
      {children}
    </NavLink>
  );
}

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Semáforo Territorial GeoTón</title>
        <Meta />
        <Links />
      </head>

      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <div className="brand">
              <div className="brand-logo">GT</div>

              <div>
                <div className="brand-title">GeoTón</div>
                <div className="brand-subtitle">Semáforo Territorial</div>
              </div>
            </div>

            <div className="sidebar-section-label">Navegación</div>

            <nav className="sidebar-nav">
              <NavItem to="/">Resumen</NavItem>
              <NavItem to="/mapa">Mapa territorial</NavItem>
              <NavItem to="/moderados">Distritos moderados</NavItem>
              <NavItem to="/modelo">Modelo SHAP</NavItem>
            </nav>

            <div className="sidebar-footer">
              <div className="sidebar-footer-title">GeoTón Perú 2026</div>
              <div className="sidebar-footer-text">
                Categoría 3 · Territorio Conectado
              </div>
            </div>
          </aside>

          <div className="main-area">
            <header className="topbar">
              <div>
                <div className="topbar-eyebrow">Observatorio territorial</div>
                <div className="topbar-title">
                  Desiertos de servicios en el Perú
                </div>
              </div>

              <div className="topbar-badge">Datos distritales · 1,874</div>
            </header>

            <main className="content">{children}</main>
          </div>
        </div>

        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  return <Outlet />;
}