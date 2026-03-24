import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { KpiCard } from "@/components/ui/KpiCard";
import { CampaignCard } from "@/components/ui/CampaignCard";
import { LoadingState, LoadingKpis } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { GlassCard } from "@/components/ui/GlassCard";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Activity, Award, Coins, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import type { MonthAnalysis, ActivePromosResponse, Campaign } from "@/types/api";

const FILTER_PROGRAMS = ["Todos", "Pass", "Smiles", "Azul", "⚡ Flash"] as const;

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
    <div className="space-y-8">
      {/* Hero gradient accent */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col gap-1"
      >
        <div className="accent-line w-12 mb-2" />
        <p className="text-sm text-muted-foreground">Monitoramento de campanhas de milhas em tempo real</p>
      </motion.div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {FILTER_PROGRAMS.map(f => (
          <button
            key={f}
            onClick={() => setSearchParams(f === "Todos" ? {} : { filter: f })}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
              filter === f
                ? "brand-gradient text-primary-foreground shadow-lg shadow-primary/20"
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
          <KpiCard label="Campanhas mês" value={month.total_campaigns} sub={`${month.delta_campaigns >= 0 ? '+' : ''}${month.delta_campaigns} vs anterior`} accent="brand" icon={<Activity className="h-4 w-4" />} delay={0} />
          <KpiCard label="Melhor bônus" value={month.best_bonus != null ? `${month.best_bonus}%` : '—'} sub="no mês corrente" accent="green" icon={<Award className="h-4 w-4" />} delay={1} />
          <KpiCard label="CPM mínimo" value={month.min_cpm != null ? `R$${month.min_cpm.toFixed(2).replace('.', ',')}/1k` : '—'} sub="por 1k milhas" accent="blue" icon={<Coins className="h-4 w-4" />} delay={2} />
          <KpiCard label="Flash sales" value={month.flash_count} sub={`${month.active_count} ativas`} accent="red" icon={<Zap className="h-4 w-4" />} delay={3} />
        </div>
      )}

      {/* Chart */}
      {month?.by_day && month.by_day.length > 0 && (
        <GlassCard animate delay={4}>
          <h2 className="text-xs font-heading font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Bônus máximo por dia</h2>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={month.by_day}>
              <defs>
                <linearGradient id="coralGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#E5002B" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#E5002B" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="day" tick={{ fill: '#555', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#555', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  background: 'hsl(235 30% 8% / 0.95)',
                  border: '1px solid hsl(235 18% 14%)',
                  borderRadius: 8,
                  boxShadow: '0 8px 24px hsl(265 96% 28% / 0.2)',
                }}
                labelStyle={{ color: '#999', fontSize: 11 }}
              />
              <Area type="monotone" dataKey="max_bonus" stroke="#E5002B" fill="url(#coralGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>
      )}

      {/* Active Campaigns */}
      <div>
        <h2 className="text-xs font-heading font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Campanhas ativas</h2>
        {loadActive ? <LoadingState rows={3} /> : errActive ? <ErrorState onRetry={() => rActive()} /> : (
          <div className="space-y-3">
            {filterItems(active?.items).length === 0 ? (
              <GlassCard className="py-12 text-center text-sm text-muted-foreground">Nenhuma campanha ativa no momento.</GlassCard>
            ) : filterItems(active?.items).map((c, i) => (
              <CampaignCard key={c.id} campaign={c} delay={i} />
            ))}
          </div>
        )}
      </div>

      {/* Latest */}
      <div>
        <h2 className="text-xs font-heading font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Últimas detectadas</h2>
        {loadLatest ? <LoadingState rows={3} /> : errLatest ? <ErrorState onRetry={() => rLatest()} /> : (
          <div className="space-y-2">
            {(filterItems(latest) ?? []).length === 0 ? (
              <GlassCard className="py-12 text-center text-sm text-muted-foreground">Nenhuma campanha recente.</GlassCard>
            ) : filterItems(latest)?.map((c, i) => (
              <CampaignCard key={c.id} campaign={c} compact delay={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
