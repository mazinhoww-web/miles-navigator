import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { KpiCard } from "@/components/ui/KpiCard";
import { LoadingState, LoadingKpis } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Lightbulb, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import type { HistoryResponse, SeasonalityData, InsightItem } from "@/types/api";

const MONTHS_OPTIONS = [3, 6, 12, 18, 24, 36];
const MONTH_NAMES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const tooltipStyle = { background: 'hsl(235 30% 8% / 0.95)', border: '1px solid hsl(235 18% 14%)', borderRadius: 8 };

export default function Historico() {
  const [sp, setSp] = useSearchParams();
  const origin = sp.get("origin") ?? "";
  const destination = sp.get("destination") ?? "";
  const months = parseInt(sp.get("months") ?? "12");

  const setParam = (key: string, val: string) => {
    const next = new URLSearchParams(sp);
    val ? next.set(key, val) : next.delete(key);
    setSp(next);
  };

  const hasRoute = !!origin && !!destination;

  const { data: history, isLoading, error, refetch } = useQuery({
    queryKey: ["history", origin, destination, months],
    queryFn: () => apiFetch<HistoryResponse>(`/api/history?origin=${origin}&destination=${destination}&months=${months}`),
    enabled: hasRoute,
    staleTime: 60_000,
  });

  const { data: seasonality } = useQuery({
    queryKey: ["seasonality"],
    queryFn: () => apiFetch<SeasonalityData>("/api/history/seasonality"),
    staleTime: 300_000,
  });

  const { data: insights } = useQuery({
    queryKey: ["insights"],
    queryFn: () => apiFetch<{ items: InsightItem[] }>("/api/history/insights"),
    staleTime: 300_000,
  });

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="accent-line w-10 mb-2" />
        <p className="text-sm text-muted-foreground">Analise padrões históricos e sazonalidade de campanhas</p>
      </motion.div>

      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            placeholder="Origem (ex: Livelo)"
            value={origin}
            onChange={e => setParam("origin", e.target.value)}
            className="glass-card pl-9 pr-3 py-2.5 text-sm bg-transparent text-foreground outline-none w-44 focus:ring-1 focus:ring-primary/30 transition-all"
          />
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            placeholder="Destino (ex: Smiles)"
            value={destination}
            onChange={e => setParam("destination", e.target.value)}
            className="glass-card pl-9 pr-3 py-2.5 text-sm bg-transparent text-foreground outline-none w-48 focus:ring-1 focus:ring-primary/30 transition-all"
          />
        </div>
        <div className="flex gap-1">
          {MONTHS_OPTIONS.map(m => (
            <button key={m} onClick={() => setParam("months", String(m))}
              className={cn("px-3 py-2 rounded-lg text-xs font-medium transition-all",
                months === m ? "brand-gradient text-primary-foreground shadow-sm" : "glass-card text-muted-foreground hover:text-foreground"
              )}>
              {m}m
            </button>
          ))}
        </div>
      </div>

      {/* Insights */}
      {insights?.items && insights.items.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {insights.items.map((item, i) => (
            <GlassCard key={i} animate delay={i} className="flex items-start gap-3">
              <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                <Lightbulb className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="text-sm leading-relaxed">{item.text}</p>
                <span className="text-xs font-heading font-bold text-primary mt-1 block">{item.metric}: {item.metric_value}</span>
              </div>
            </GlassCard>
          ))}
        </div>
      )}

      {/* Route metrics */}
      {hasRoute && (
        isLoading ? <LoadingKpis count={6} /> : error ? <ErrorState onRetry={() => refetch()} /> : history?.route_metrics && (
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            <KpiCard label="Freq/mês" value={history.route_metrics.freq_per_month.toFixed(1)} accent="brand" delay={0} />
            <KpiCard label="Duração média" value={`${history.route_metrics.avg_duration}d`} accent="blue" delay={1} />
            <KpiCard label="Bônus médio" value={`${history.route_metrics.avg_bonus}%`} accent="green" delay={2} />
            <KpiCard label="Bônus máx histórico" value={`${history.route_metrics.max_bonus}%`} accent="brand" delay={3} />
            <KpiCard label="CPM mínimo" value={`R$${history.route_metrics.min_cpm.toFixed(2).replace('.', ',')}/1k`} accent="green" delay={4} />
            <KpiCard label="Próxima janela" value={history.route_metrics.next_window_est ?? '—'} accent="purple" delay={5} />
          </div>
        )
      )}

      {history?.monthly_series && history.monthly_series.length > 0 && (
        <GlassCard animate delay={6}>
          <h3 className="text-xs font-heading font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Histórico de bônus</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={history.monthly_series}>
              <XAxis dataKey="month" tick={{ fill: '#555', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#555', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="bonus_avg" stroke="#E5002B" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </GlassCard>
      )}

      {!hasRoute && !insights?.items?.length && (
        <GlassCard className="py-16 text-center">
          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
            <Search className="h-6 w-6 text-primary" />
          </div>
          <p className="text-sm text-muted-foreground">Selecione origem e destino para ver o histórico da rota.</p>
        </GlassCard>
      )}

      {/* Seasonality heatmap */}
      {seasonality?.grid && seasonality.grid.length > 0 && (
        <GlassCard animate delay={7}>
          <h3 className="text-xs font-heading font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Sazonalidade</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th className="text-left py-2 pr-3 text-muted-foreground uppercase tracking-wider text-[10px]">Programa</th>
                  {MONTH_NAMES.map(m => <th key={m} className="py-2 px-1 text-center text-muted-foreground text-[10px]">{m}</th>)}
                </tr>
              </thead>
              <tbody>
                {seasonality.grid.map(row => (
                  <tr key={row.program}>
                    <td className="py-2 pr-3 font-medium">{row.program}</td>
                    {row.months.map((val, i) => {
                      const bg = val > 1.2 ? `rgba(229,0,43,${Math.min(val / 2, 0.6)})`
                               : val > 0.8 ? `rgba(229,0,43,${Math.min(val / 3, 0.3)})`
                               : `rgba(107,114,128,0.1)`;
                      return (
                        <td key={i} className="py-2 px-1 text-center" title={`${row.program} - ${MONTH_NAMES[i]}: ${val.toFixed(2)}`}>
                          <div className="w-9 h-7 rounded-md flex items-center justify-center mx-auto text-[10px] font-medium" style={{ background: bg }}>
                            {val.toFixed(1)}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
