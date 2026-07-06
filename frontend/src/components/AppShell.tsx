import { useState, type ReactNode } from "react";

type RouteItem = {
  path: string;
  label: string;
  title: string;
};

type AppShellProps = {
  routes: RouteItem[];
  currentPath: string;
  title: string;
  hideHeader?: boolean;
  onNavigate: (path: string) => void;
  children: ReactNode;
};

export function AppShell({ routes, currentPath, title, hideHeader = false, onNavigate, children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navigateFromSidebar = (path: string) => {
    onNavigate(path);
    setSidebarOpen(false);
  };

  return (
    <div className={`${sidebarOpen ? "workspace-shell sidebar-open" : "workspace-shell"}${hideHeader ? " header-hidden" : ""}`}>
      <button
        type="button"
        className="sidebar-summon"
        onClick={() => setSidebarOpen(true)}
        aria-label="Open navigation"
        aria-expanded={sidebarOpen}
      >
        <span />
        <span />
      </button>

      <button
        type="button"
        className="sidebar-backdrop"
        onClick={() => setSidebarOpen(false)}
        aria-label="Close navigation"
        tabIndex={sidebarOpen ? 0 : -1}
      />

      <aside className="workspace-sidebar" data-collapse-ready="true" aria-hidden={!sidebarOpen}>
        <div className="workspace-brand">
          <div className="workspace-brand-mark">A</div>
          <div className="workspace-brand-copy">
            <strong>ATHENA</strong>
            <span>Executive OS</span>
          </div>
        </div>

        <button
          type="button"
          className="sidebar-toggle"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation"
        >
          <span />
          <span />
        </button>

        <nav className="workspace-nav" aria-label="Primary navigation">
          {routes.map((route) => (
            <button
              key={route.path}
              type="button"
              className={route.path === currentPath ? "workspace-nav-item active" : "workspace-nav-item"}
              onClick={() => navigateFromSidebar(route.path)}
            >
              <span>{route.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <div className="workspace-main">
        {!hideHeader && (
          <header className="workspace-topbar">
            <div>
              <span className="topbar-label">ATHENA Chamber</span>
              <h1>{title}</h1>
            </div>

            <div className="status-cluster">
              <span className="status-dot" />
              <span>ATHENA Online</span>
            </div>
          </header>
        )}

        <main className="workspace-content">{children}</main>
      </div>
    </div>
  );
}
