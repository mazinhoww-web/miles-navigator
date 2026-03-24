import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { KpiCard } from "@/components/ui/KpiCard";
import { LoadingState, LoadingKpis } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HistoryResponse, SeasonalityData, InsightItem } from "@/types/api";

const MONTHS_OPTIONS = [3, 6, 12, 18, 24, 36];
const MONTH_NAMES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

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
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          placeholder="Origem (ex: Livelo)"
          value={origin}
          onChange={e => setParam("origin", e.target.value)}
          className="glass-card px-3 py-2 text-sm bg-transparent text-foreground outline-none w-40"
        />
        <input
          placeholder="Destino (ex: LATAM Pass)"
          value={destination}
          onChange={e => setParam("destination", e.target.value)}
          className="glass-card px-3 py-2 text-sm bg-transparent text-foreground outline-none w-44"
        />
        <div className="flex gap-1">
          {MONTHS_OPTIONS.map(m => (
            <button
              key={m}
              onClick={() => setParam("months", String(m))}
              className={cn("px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                months === m ? "bg-primary text-primary-foreground" : "glass-card text-muted-foreground hover:text-foreground"
              )}
            >
              {m}m
            </button>
          ))}
        </div>
      </div>

      {/* Insights */}
      {insights?.items && insights.items.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {insights.items.map((item, i) => (
            <GlassCard key={i} className="flex items-start gap-3">
              <Lightbulb className="h-5 w-5 text-primary shrink-0 mt-0.5" />
              <div>
                <p className="text-sm">{item.text}</p>
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
            <KpiCard label="Freq/mês" value={history.route_metrics.freq_per_month.toFixed(1)} accent="gold" />
            <KpiCard label="Duração média" value={`${history.route_metrics.avg_duration}d`} accent="blue" />
            <KpiCard label="Bônus médio" value={`${history.route_metrics.avg_bonus}%`} accent="green" />
            <KpiCard label="Bônus máx histórico" value={`${history.route_metrics.max_bonus}%`} accent="gold" />
            <KpiCard label="CPM mínimo" value={`R$${history.route_metrics.min_cpm.toFixed(2).replace('.', ',')}/1k`} accent="green" />
            <KpiCard label="Próxima janela" value={history.route_metrics.next_window_est ?? '—'} accent="purple" />
          </div>
        )
      )}

      {/* History chart */}
      {history?.monthly_series && history.monthly_series.length > 0 && (
        <GlassCard>
          <h3 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Histórico de bônus</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={history.monthly_series}>
              <XAxis dataKey="month" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
              <Line type="monotone" dataKey="bonus_avg" stroke="#3B82F6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </GlassCard>
      )}

      {!hasRoute && !insights?.items?.length && (
        <GlassCard className="py-12 text-center text-sm text-muted-foreground">
          Selecione origem e destino para ver o histórico da rota.
        </GlassCard>
      )}

      {/* Seasonality heatmap */}
      {seasonality?.grid && seasonality.grid.length > 0 && (
        <GlassCard>
          <h3 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Sazonalidade</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th className="text-left py-2 pr-3 text-muted-foreground">Programa</th>
                  {MONTH_NAMES.map(m => <th key={m} className="py-2 px-1 text-center text-muted-foreground">{m}</th>)}
                </tr>
              </thead>
              <tbody>
                {seasonality.grid.map(row => (
                  <tr key={row.program}>
                    <td className="py-1.5 pr-3 font-medium">{row.program}</td>
                    {row.months.map((val, i) => {
                      const intensity = Math.min(val / 1.5, 1);
                      const bg = val > 1.2 ? `rgba(245,158,11,${intensity * 0.6})` 
                               : val > 0.8 ? `rgba(245,158,11,${intensity * 0.3})`
                               : `rgba(107,114,128,${0.1 + intensity * 0.1})`;
                      return (
                        <td key={i} className="py-1.5 px-1 text-center" title={`${row.program} - ${MONTH_NAMES[i]}: ${val.toFixed(2)}`}>
                          <div className="w-8 h-6 rounded flex items-center justify-center mx-auto text-[10px]" style={{ background: bg }}>
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
