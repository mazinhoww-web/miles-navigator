import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { KpiCard } from "@/components/ui/KpiCard";
import { CampaignCard } from "@/components/ui/CampaignCard";
import { LoadingState, LoadingKpis } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { GlassCard } from "@/components/ui/GlassCard";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts";
import { Activity, Award, Coins, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MonthAnalysis, ActivePromosResponse, Campaign } from "@/types/api";

const FILTER_PROGRAMS = ["Todos", "LATAM Pass", "Smiles", "Azul", "⚡ Flash"] as const;

export default function Monitor() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filter = searchParams.get("filter") ?? "Todos";

  const { data: month, isLoading: loadMonth, error: errMonth, refetch: rMonth } = useQuery({
    queryKey: ["analysis-month"],
    queryFn: () => apiFetch<MonthAnalysis>("/api/analysis/month"),
    refetchInterval: 120_000,
    staleTime: 60_000,
  });

  const { data: active, isLoading: loadActive, error: errActive, refetch: rActive } = useQuery({
    queryKey: ["promos-active"],
    queryFn: () => apiFetch<ActivePromosResponse>("/api/promos/active"),
    refetchInterval: 120_000,
    staleTime: 60_000,
  });

  const { data: latest, isLoading: loadLatest, error: errLatest, refetch: rLatest } = useQuery({
    queryKey: ["promos-latest"],
    queryFn: () => apiFetch<Campaign[]>("/api/promos?limit=10&order=detected_at"),
    refetchInterval: 120_000,
    staleTime: 60_000,
  });

  const filterItems = (items: Campaign[] | undefined) => {
    if (!items) return [];
    if (filter === "Todos") return items;
    if (filter === "⚡ Flash") return items.filter(c => c.is_flash);
    return items.filter(c =>
      c.destination_program?.toLowerCase().includes(filter.toLowerCase()) ||
      c.origin_program?.toLowerCase().includes(filter.toLowerCase())
    );
  };

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {FILTER_PROGRAMS.map(f => (
          <button
            key={f}
            onClick={() => setSearchParams(f === "Todos" ? {} : { filter: f })}
            className={cn(
              "px-4 py-1.5 rounded-full text-sm font-medium transition-colors",
              filter === f
                ? "bg-primary text-primary-foreground"
                : "glass-card text-muted-foreground hover:text-foreground"
            )}
          >
            {f}
          </button>
        ))}
      </div>

      {/* KPIs */}
      {loadMonth ? <LoadingKpis /> : errMonth ? <ErrorState onRetry={() => rMonth()} /> : month && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard label="Campanhas mês" value={month.total_campaigns} sub={`${month.delta_campaigns >= 0 ? '+' : ''}${month.delta_campaigns} vs anterior`} accent="gold" icon={<Activity className="h-4 w-4" />} />
          <KpiCard label="Melhor bônus" value={month.best_bonus != null ? `${month.best_bonus}%` : '—'} sub="no mês corrente" accent="green" icon={<Award className="h-4 w-4" />} />
          <KpiCard label="CPM mínimo" value={month.min_cpm != null ? `R$${month.min_cpm.toFixed(2).replace('.', ',')}/1k` : '—'} sub="por 1k milhas" accent="blue" icon={<Coins className="h-4 w-4" />} />
          <KpiCard label="Flash sales" value={month.flash_count} sub={`${month.active_count} ativas`} accent="red" icon={<Zap className="h-4 w-4" />} />
        </div>
      )}

      {/* Chart */}
      {month?.by_day && month.by_day.length > 0 && (
        <GlassCard>
          <h2 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Bônus máximo por dia</h2>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={month.by_day}>
              <defs>
                <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F59E0B" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#F59E0B" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
              <Area type="monotone" dataKey="max_bonus" stroke="#F59E0B" fill="url(#goldGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>
      )}

      {/* Active Campaigns */}
      <div>
        <h2 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Campanhas ativas</h2>
        {loadActive ? <LoadingState rows={3} /> : errActive ? <ErrorState onRetry={() => rActive()} /> : (
          <div className="space-y-3">
            {filterItems(active?.items).length === 0 ? (
              <GlassCard className="py-8 text-center text-sm text-muted-foreground">Nenhuma campanha ativa no momento.</GlassCard>
            ) : filterItems(active?.items).map(c => (
              <CampaignCard key={c.id} campaign={c} />
            ))}
          </div>
        )}
      </div>

      {/* Latest */}
      <div>
        <h2 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Últimas detectadas</h2>
        {loadLatest ? <LoadingState rows={3} /> : errLatest ? <ErrorState onRetry={() => rLatest()} /> : (
          <div className="space-y-2">
            {(filterItems(latest) ?? []).length === 0 ? (
              <GlassCard className="py-8 text-center text-sm text-muted-foreground">Nenhuma campanha recente.</GlassCard>
            ) : filterItems(latest)?.map(c => (
              <CampaignCard key={c.id} campaign={c} compact />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
