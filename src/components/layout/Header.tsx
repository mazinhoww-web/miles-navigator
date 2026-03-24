import { useLocation } from "react-router-dom";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Wifi } from "lucide-react";

const titles: Record<string, string> = {
  "/": "Monitor em Tempo Real",
  "/analise-mensal": "Análise Mensal",
  "/historico": "Histórico de Campanhas",
  "/vpp": "VPP — Valor Por Ponto",
  "/previsao": "Previsão de Campanhas",
  "/watchlist": "Watchlist",
  "/status": "Status do Sistema",
};

export function Header() {
  const { pathname } = useLocation();
  const title = pathname.startsWith("/campanha/") ? "Detalhes da Campanha" : (titles[pathname] ?? "Miles Radar");

  return (
    <header className="sticky top-0 z-20 h-14 border-b border-border bg-background/70 backdrop-blur-xl flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <h1 className="font-heading font-bold text-base text-foreground">{title}</h1>
        <div className="accent-line w-8 hidden sm:block" />
      </div>
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <Wifi className="h-3 w-3 text-miles-green" />
          <span className="hidden sm:inline">Online</span>
        </span>
        <span className="hidden sm:inline">Atualizado {format(new Date(), "HH:mm", { locale: ptBR })}</span>
      </div>
    </header>
  );
}
