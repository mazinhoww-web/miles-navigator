import { useLocation } from "react-router-dom";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

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
    <header className="sticky top-0 z-20 h-14 border-b border-border bg-background/80 backdrop-blur-md flex items-center justify-between px-6">
      <h1 className="font-heading font-bold text-lg">{title}</h1>
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-miles-green" />
          Online
        </span>
        <span>Atualizado {format(new Date(), "HH:mm", { locale: ptBR })}</span>
      </div>
    </header>
  );
}
