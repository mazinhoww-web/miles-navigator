import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard, CalendarDays, BarChart3, DollarSign,
  TrendingUp, Bookmark, Server, Menu, X, Plane, Bot
} from "lucide-react";
import latamIcon from "@/assets/latam-pass-icon.png";

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
        className="fixed top-4 left-4 z-50 lg:hidden glass-card p-2.5 rounded-lg"
      >
        {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Overlay */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-30 lg:hidden"
            onClick={() => setOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside className={cn(
        "fixed top-0 left-0 z-40 h-screen w-60 bg-sidebar flex flex-col transition-transform duration-300 ease-out",
        "border-r border-sidebar-border",
        open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-sidebar-border">
          <img src={latamIcon} alt="LATAM Pass" className="h-8 w-8 object-contain" />
          <div className="flex flex-col">
            <span className="font-heading font-bold text-sm tracking-tight text-foreground">Miles Radar</span>
            <span className="text-[10px] text-muted-foreground tracking-widest uppercase">LATAM Pass</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-widest px-3 mb-2 block">
            Análise
          </span>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              onClick={() => setOpen(false)}
              className={({ isActive }) => cn(
                "group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 relative",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              )}
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-active"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 brand-gradient rounded-r-full"
                      transition={{ type: "spring", stiffness: 400, damping: 30 }}
                    />
                  )}
                  <item.icon className={cn("h-4 w-4 shrink-0 transition-colors", isActive && "text-primary")} />
                  <span className="truncate">{item.label}</span>
                  {item.badge && (
                    <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded-md bg-accent/50 text-muted-foreground font-medium">
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          ))}

          <div className="border-t border-sidebar-border my-4" />

          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-widest px-3 mb-2 block">
            Sistema
          </span>

          <NavLink
            to="/status"
            onClick={() => setOpen(false)}
            className={({ isActive }) => cn(
              "group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 relative",
              isActive
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
            )}
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 brand-gradient rounded-r-full"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <Server className={cn("h-4 w-4 shrink-0 transition-colors", isActive && "text-primary")} />
                <span>Status</span>
                <span className="ml-auto h-2 w-2 rounded-full bg-miles-green animate-pulse-soft" />
              </>
            )}
          </NavLink>

          <NavLink
            to="/apify"
            onClick={() => setOpen(false)}
            className={({ isActive }) => cn(
              "group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 relative",
              isActive
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
            )}
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 brand-gradient rounded-r-full"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <Bot className={cn("h-4 w-4 shrink-0 transition-colors", isActive && "text-primary")} />
                <span>Apify Actors</span>
              </>
            )}
          </NavLink>
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-sidebar-border">
          <div className="flex items-center gap-2">
            <Plane className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] text-muted-foreground">Inteligência de Milhas</span>
          </div>
        </div>
      </aside>
    </>
  );
}
