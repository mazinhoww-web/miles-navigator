import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { KpiCard } from "@/components/ui/KpiCard";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingState, LoadingKpis } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from "recharts";
import { Activity, Award, Coins, Zap, TrendingUp, Calendar } from "lucide-react";
import type { MonthAnalysis, Campaign } from "@/types/api";

const PIE_COLORS = ["#F59E0B", "#3B82F6", "#8B5CF6", "#EF4444", "#10B981", "#6b7280"];
const TYPE_LABELS: Record<string, string> = {
  transfer_bonus: "Bônus Transferência",
  direct_purchase: "Compra Direta",
  club_combo: "Clube + Combo",
  flash_sale: "Flash Sale",
  club_signup: "Assinatura Clube",
  other: "Outro",
};

export default function AnaliseMensal() {
  const [month, setMonth] = useState(() => format(new Date(), "yyyy-MM"));

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["analysis-month", month],
    queryFn: () => apiFetch<MonthAnalysis>(`/api/analysis/month?month=${month}`),
    staleTime: 60_000,
  });

  const { data: campaigns } = useQuery({
    queryKey: ["month-campaigns", month],
    queryFn: () => apiFetch<Campaign[]>(`/api/promos?month=${month}&limit=50`),
    staleTime: 60_000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <input
          type="month"
          value={month}
          onChange={e => setMonth(e.target.value)}
          className="glass-card px-3 py-2 text-sm bg-transparent text-foreground outline-none"
        />
      </div>

      {isLoading ? <LoadingKpis count={6} /> : error ? <ErrorState onRetry={() => refetch()} /> : data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            <KpiCard label="Total campanhas" value={data.total_campaigns} accent="gold" icon={<Activity className="h-4 w-4" />} />
            <KpiCard label="Novas" value={data.new_campaigns} accent="blue" icon={<TrendingUp className="h-4 w-4" />} />
            <KpiCard label="Melhor bônus" value={data.best_bonus != null ? `${data.best_bonus}%` : '—'} accent="green" icon={<Award className="h-4 w-4" />} />
            <KpiCard label="CPM mínimo" value={data.min_cpm != null ? `R$${data.min_cpm.toFixed(2).replace('.', ',')}/1k` : '—'} accent="blue" icon={<Coins className="h-4 w-4" />} />
            <KpiCard label="Flash sales" value={data.flash_count} accent="red" icon={<Zap className="h-4 w-4" />} />
            <KpiCard label="Ativas" value={data.active_count} accent="purple" icon={<Calendar className="h-4 w-4" />} />
          </div>

          {/* Line chart */}
          {data.by_day?.length > 0 && (
            <GlassCard>
              <h3 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Bônus por dia</h3>
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={data.by_day}>
                  <defs>
                    <linearGradient id="goldG" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#F59E0B" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#F59E0B" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                  <Area type="monotone" dataKey="max_bonus" stroke="#F59E0B" fill="url(#goldG)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </GlassCard>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Bar chart - programs */}
            {data.by_program?.length > 0 && (
              <GlassCard>
                <h3 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Distribuição por programa</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={data.by_program} layout="vertical">
                    <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="program" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} width={100} />
                    <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                    <Bar dataKey="count" fill="#F59E0B" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </GlassCard>
            )}

            {/* Pie chart - types */}
            {data.by_type?.length > 0 && (
              <GlassCard>
                <h3 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Distribuição por tipo</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={data.by_type.map(t => ({ ...t, name: TYPE_LABELS[t.promo_type] ?? t.promo_type }))}
                      dataKey="count"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {data.by_type.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                  </PieChart>
                </ResponsiveContainer>
              </GlassCard>
            )}
          </div>
        </>
      )}

      {/* Campaigns table */}
      {campaigns && campaigns.length > 0 && (
        <GlassCard>
          <h3 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Campanhas do mês</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-muted-foreground border-b border-border">
                  <th className="text-left py-2 pr-3">Data</th>
                  <th className="text-left py-2 pr-3">Título</th>
                  <th className="text-left py-2 pr-3">Rota</th>
                  <th className="text-right py-2 pr-3">Bônus</th>
                  <th className="text-right py-2 pr-3">VPP</th>
                  <th className="text-left py-2">Tipo</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map(c => (
                  <tr key={c.id} className="border-b border-border/50 hover:bg-white/[0.02]">
                    <td className="py-2 pr-3 text-muted-foreground">{c.detected_at ? format(new Date(c.detected_at), "dd/MM", { locale: ptBR }) : '—'}</td>
                    <td className="py-2 pr-3 truncate max-w-[200px]">{c.title}</td>
                    <td className="py-2 pr-3 text-xs">{c.origin_program ?? '—'} → {c.destination_program ?? '—'}</td>
                    <td className="text-right py-2 pr-3 font-heading font-bold text-primary">{c.bonus_pct_max ?? '—'}%</td>
                    <td className="text-right py-2 pr-3 text-miles-green">{c.vpp_real_base != null ? `R$${c.vpp_real_base.toFixed(2).replace('.', ',')}` : '—'}</td>
                    <td className="py-2 text-xs text-muted-foreground">{TYPE_LABELS[c.promo_type] ?? c.promo_type}</td>
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
