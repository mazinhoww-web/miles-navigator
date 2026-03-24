import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Progress } from "@/components/ui/progress";
import { AlertTriangle, Calendar, Target } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import type { PredictionRoute, PredictionEvent } from "@/types/api";

const HORIZONS = [7, 15, 30, 60];

const urgencyMap: Record<string, { label: string; cls: string }> = {
  imminent: { label: "AÇÃO IMINENTE", cls: "bg-primary/15 text-primary border-primary/20" },
  high: { label: "ALTA PROB", cls: "bg-amber-500/12 text-amber-400 border-amber-500/20" },
  monitor: { label: "MONITORAR", cls: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
  wait: { label: "AGUARDAR", cls: "bg-secondary text-muted-foreground border-border" },
};

export default function Previsao() {
  const [sp, setSp] = useSearchParams();
  const horizon = parseInt(sp.get("horizon") ?? "30");

  const setParam = (k: string, v: string) => {
    const next = new URLSearchParams(sp);
    next.set(k, v);
    setSp(next);
  };

  const { data: predictions, isLoading, error, refetch } = useQuery({
    queryKey: ["predictions", horizon],
    queryFn: () => apiFetch<{ predictions: PredictionRoute[] }>(`/api/predictions/all?horizon=${horizon}`),
    staleTime: 60_000,
  });

  const { data: events } = useQuery({
    queryKey: ["prediction-events"],
    queryFn: () => apiFetch<PredictionEvent[]>("/api/predictions/events?days_ahead=180"),
    staleTime: 300_000,
  });

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="accent-line w-10 mb-2" />
        <p className="text-sm text-muted-foreground">Previsões baseadas em padrões históricos de campanhas</p>
      </motion.div>

      {/* Disclaimer */}
      <GlassCard accentColor="red" className="border-l-4" animate delay={0}>
        <div className="flex items-start gap-3">
          <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <AlertTriangle className="h-4 w-4 text-primary" />
          </div>
          <p className="text-sm leading-relaxed">
            Previsões baseadas em padrões históricos. <strong className="text-foreground">Não garantem campanhas futuras.</strong> Use como referência de planejamento, não como certeza.
          </p>
        </div>
      </GlassCard>

      {/* Controls */}
      <div className="flex gap-2">
        {HORIZONS.map(h => (
          <button key={h} onClick={() => setParam("horizon", String(h))}
            className={cn("px-4 py-2 rounded-lg text-sm font-medium transition-all",
              horizon === h ? "brand-gradient text-primary-foreground shadow-sm" : "glass-card text-muted-foreground hover:text-foreground"
            )}>
            {h} dias
          </button>
        ))}
      </div>

      {/* Prediction cards */}
      {isLoading ? <LoadingState rows={5} /> : error ? <ErrorState onRetry={() => refetch()} /> : predictions?.predictions && (
        <div className="space-y-3">
          <h3 className="text-xs font-heading font-semibold text-muted-foreground uppercase tracking-wider">Top rotas por probabilidade</h3>
          {predictions.predictions.length === 0 ? (
            <GlassCard className="py-16 text-center">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                <Target className="h-6 w-6 text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">Nenhuma previsão disponível.</p>
            </GlassCard>
          ) : predictions.predictions.slice(0, 5).map((p, i) => {
            const u = urgencyMap[p.urgency] ?? urgencyMap.wait;
            return (
              <GlassCard key={i} animate delay={i + 1}>
                <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                  <span className="font-heading font-semibold">{p.origin} → {p.destination}</span>
                  <span className={cn("text-[10px] px-2.5 py-1 rounded-md font-bold tracking-wider border", u.cls)}>{u.label}</span>
                </div>
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-xs text-muted-foreground">P({horizon}d) =</span>
                  <span className="font-heading font-bold text-primary text-xl">{p.probability_30d}%</span>
                  <Progress value={p.probability_30d} className="flex-1 h-2" />
                </div>
                <p className="text-xs text-muted-foreground mb-2">Bônus esperado: <span className="text-foreground font-medium">{p.bonus_range_low}–{p.bonus_range_high}%</span></p>
                {p.evidence?.length > 0 && (
                  <ul className="text-xs text-muted-foreground space-y-1 mt-3 pl-1 border-l-2 border-primary/20 ml-1">
                    {p.evidence.slice(0, 3).map((e, j) => <li key={j} className="pl-3">{e}</li>)}
                  </ul>
                )}
              </GlassCard>
            );
          })}
        </div>
      )}

      {/* Heatmap */}
      {predictions?.predictions && predictions.predictions.length > 0 && (() => {
        const origins = [...new Set(predictions.predictions.map(p => p.origin))];
        const destinations = [...new Set(predictions.predictions.map(p => p.destination))];
        const getProb = (o: string, d: string) => predictions.predictions.find(p => p.origin === o && p.destination === d)?.probability_30d;
        return (
          <GlassCard animate delay={6}>
            <h3 className="text-xs font-heading font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Heatmap de probabilidade</h3>
            <div className="overflow-x-auto">
              <table className="text-xs">
                <thead>
                  <tr>
                    <th className="py-2 pr-3 text-left text-muted-foreground text-[10px] uppercase tracking-wider">Origem / Destino</th>
                    {destinations.map(d => <th key={d} className="py-2 px-2 text-center text-muted-foreground text-[10px]">{d}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {origins.map(o => (
                    <tr key={o}>
                      <td className="py-2 pr-3 font-medium">{o}</td>
                      {destinations.map(d => {
                        const prob = getProb(o, d);
                        const bg = prob == null ? 'transparent'
                          : prob > 70 ? `rgba(229,0,43,0.5)`
                          : prob > 40 ? `rgba(229,0,43,0.25)`
                          : `rgba(107,114,128,0.1)`;
                        return (
                          <td key={d} className="py-2 px-2 text-center">
                            {prob != null && (
                              <div className="w-11 h-7 rounded-md flex items-center justify-center mx-auto font-medium" style={{ background: bg }}>
                                {prob}%
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        );
      })()}

      {/* Events */}
      {events && events.length > 0 && (
        <div>
          <h3 className="text-xs font-heading font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Calendário de eventos recorrentes</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {events.sort((a, b) => a.days_remaining - b.days_remaining).map((ev, i) => (
              <GlassCard key={i} accentColor={ev.days_remaining < 30 ? 'red' : undefined} animate delay={i + 7}>
                <div className="flex items-start gap-3">
                  <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <Calendar className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <p className="font-heading font-semibold text-sm">{ev.name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{ev.expected_date} • <span className={ev.days_remaining < 30 ? "text-primary font-medium" : ""}>{ev.days_remaining} dias restantes</span></p>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{ev.description}</p>
                    <div className="flex gap-1 mt-2 flex-wrap">
                      {ev.programs.map(p => <span key={p} className="text-[10px] px-2 py-0.5 rounded-md bg-secondary text-muted-foreground font-medium">{p}</span>)}
                    </div>
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
