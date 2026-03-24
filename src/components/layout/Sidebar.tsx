import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard, CalendarDays, BarChart3, DollarSign,
  TrendingUp, Bookmark, Server, Menu, X, Radar
} from "lucide-react";

const navItems = [
  { label: "Monitor", path: "/", icon: LayoutDashboard },
  { label: "Análise Mensal", path: "/analise-mensal", icon: CalendarDays },
  { label: "Histórico", path: "/historico", icon: BarChart3, badge: "Fase 3" },
  { label: "VPP", path: "/vpp", icon: DollarSign, badge: "Fase 4" },
  { label: "Previsão", path: "/previsao", icon: TrendingUp, badge: "Fase 5" },
  { label: "Watchlist", path: "/watchlist", icon: Bookmark },
];

export function Sidebar() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed top-4 left-4 z-50 lg:hidden glass-card p-2"
      >
        {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Overlay */}
      {open && <div className="fixed inset-0 bg-black/60 z-30 lg:hidden" onClick={() => setOpen(false)} />}

      {/* Sidebar */}
      <aside className={cn(
        "fixed top-0 left-0 z-40 h-screen w-56 bg-sidebar border-r border-sidebar-border flex flex-col transition-transform duration-200",
        open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        <div className="flex items-center gap-2 px-5 py-5 border-b border-sidebar-border">
          <Radar className="h-6 w-6 text-primary" />
          <span className="font-heading font-bold text-lg text-foreground">Miles Radar</span>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              onClick={() => setOpen(false)}
              className={({ isActive }) => cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-primary"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{item.label}</span>
              {item.badge && (
                <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{item.badge}</span>
              )}
            </NavLink>
          ))}

          <div className="border-t border-sidebar-border my-3" />

          <NavLink
            to="/status"
            onClick={() => setOpen(false)}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              isActive
                ? "bg-sidebar-accent text-primary"
                : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            )}
          >
            <Server className="h-4 w-4 shrink-0" />
            <span>Status</span>
            <span className={cn("ml-auto h-2 w-2 rounded-full", "bg-miles-green")} />
          </NavLink>
        </nav>
      </aside>
    </>
  );
}
