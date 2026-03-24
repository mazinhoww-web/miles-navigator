import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Progress } from "@/components/ui/progress";
import { AlertTriangle, Calendar } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PredictionRoute, PredictionEvent } from "@/types/api";

const HORIZONS = [7, 15, 30, 60];

const urgencyMap: Record<string, { label: string; cls: string }> = {
  imminent: { label: "AÇÃO IMINENTE", cls: "bg-red-500/15 text-red-400" },
  high: { label: "ALTA PROB", cls: "bg-yellow-500/15 text-yellow-400" },
  monitor: { label: "MONITORAR", cls: "bg-blue-500/15 text-blue-400" },
  wait: { label: "AGUARDAR", cls: "bg-gray-500/15 text-gray-400" },
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
    <div className="space-y-6">
      {/* Disclaimer */}
      <GlassCard accentColor="red" className="border-l-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-miles-red shrink-0 mt-0.5" />
          <p className="text-sm">
            ⚠️ Previsões baseadas em padrões históricos. Não garantem campanhas futuras. Use como referência de planejamento, não como certeza.
          </p>
        </div>
      </GlassCard>

      {/* Controls */}
      <div className="flex gap-2">
        {HORIZONS.map(h => (
          <button key={h} onClick={() => setParam("horizon", String(h))}
            className={cn("px-4 py-1.5 rounded-full text-sm font-medium transition-colors",
              horizon === h ? "bg-primary text-primary-foreground" : "glass-card text-muted-foreground hover:text-foreground"
            )}>
            {h} dias
          </button>
        ))}
      </div>

      {/* Prediction cards */}
      {isLoading ? <LoadingState rows={5} /> : error ? <ErrorState onRetry={() => refetch()} /> : predictions?.predictions && (
        <div className="space-y-3">
          <h3 className="text-sm font-heading font-semibold text-muted-foreground">Top rotas por probabilidade</h3>
          {predictions.predictions.length === 0 ? (
            <GlassCard className="py-8 text-center text-sm text-muted-foreground">Nenhuma previsão disponível.</GlassCard>
          ) : predictions.predictions.slice(0, 5).map((p, i) => {
            const u = urgencyMap[p.urgency] ?? urgencyMap.wait;
            return (
              <GlassCard key={i}>
                <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                  <span className="font-heading font-semibold">{p.origin} → {p.destination}</span>
                  <span className={cn("text-xs px-2 py-0.5 rounded-full font-semibold", u.cls)}>{u.label}</span>
                </div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-sm text-muted-foreground">P({horizon}d) =</span>
                  <span className="font-heading font-bold text-primary text-lg">{p.probability_30d}%</span>
                  <Progress value={p.probability_30d} className="flex-1 h-2" />
                </div>
                <p className="text-xs text-muted-foreground mb-1">Bônus esperado: {p.bonus_range_low}–{p.bonus_range_high}%</p>
                {p.evidence?.length > 0 && (
                  <ul className="text-xs text-muted-foreground space-y-0.5 mt-2">
                    {p.evidence.slice(0, 3).map((e, j) => <li key={j}>• {e}</li>)}
                  </ul>
                )}
              </GlassCard>
            );
          })}
        </div>
      )}

      {/* Prediction heatmap */}
      {predictions?.predictions && predictions.predictions.length > 0 && (() => {
        const origins = [...new Set(predictions.predictions.map(p => p.origin))];
        const destinations = [...new Set(predictions.predictions.map(p => p.destination))];
        const getProb = (o: string, d: string) => predictions.predictions.find(p => p.origin === o && p.destination === d)?.probability_30d;
        return (
          <GlassCard>
            <h3 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Heatmap de probabilidade</h3>
            <div className="overflow-x-auto">
              <table className="text-xs">
                <thead>
                  <tr>
                    <th className="py-2 pr-3 text-left text-muted-foreground">Origem / Destino</th>
                    {destinations.map(d => <th key={d} className="py-2 px-2 text-center text-muted-foreground">{d}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {origins.map(o => (
                    <tr key={o}>
                      <td className="py-1.5 pr-3 font-medium">{o}</td>
                      {destinations.map(d => {
                        const prob = getProb(o, d);
                        const bg = prob == null ? 'transparent'
                          : prob > 70 ? `rgba(245,158,11,0.6)`
                          : prob > 40 ? `rgba(245,158,11,0.3)`
                          : `rgba(107,114,128,0.15)`;
                        return (
                          <td key={d} className="py-1.5 px-2 text-center">
                            {prob != null && (
                              <div className="w-10 h-6 rounded flex items-center justify-center mx-auto" style={{ background: bg }}>
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
          <h3 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Calendário de eventos recorrentes</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {events.sort((a, b) => a.days_remaining - b.days_remaining).map((ev, i) => (
              <GlassCard key={i} accentColor={ev.days_remaining < 30 ? 'red' : undefined}>
                <div className="flex items-start gap-3">
                  <Calendar className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <div>
                    <p className="font-heading font-semibold text-sm">{ev.name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{ev.expected_date} • {ev.days_remaining} dias restantes</p>
                    <p className="text-xs text-muted-foreground mt-1">{ev.description}</p>
                    <div className="flex gap-1 mt-2 flex-wrap">
                      {ev.programs.map(p => <span key={p} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{p}</span>)}
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
