import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { KpiCard } from "@/components/ui/KpiCard";
import { OpBadge } from "@/components/ui/OpBadge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { cn } from "@/lib/utils";
import { Tooltip as UITooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Info, Calculator } from "lucide-react";
import { motion } from "framer-motion";
import type { VppCampaign } from "@/types/api";

const MONTHS_OPTIONS = [3, 6, 12, 18, 24, 36];
const VPP_TARGETS: Record<string, number> = { Smiles: 16, "Azul Fidelidade": 14, Pass: 14 };
const tooltipStyle = { background: 'hsl(235 30% 8% / 0.95)', border: '1px solid hsl(235 18% 14%)', borderRadius: 8 };

export default function VPP() {
  const [sp, setSp] = useSearchParams();
  const months = parseInt(sp.get("months") ?? "12");
  const dest = sp.get("destination") ?? "";

  const setParam = (k: string, v: string) => {
    const next = new URLSearchParams(sp);
    v ? next.set(k, v) : next.delete(k);
    setSp(next);
  };

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["vpp", dest, months],
    queryFn: () => apiFetch<VppCampaign[]>(dest ? `/api/vpp?destination=${dest}&months=${months}` : `/api/vpp/all?months=${months}`),
    staleTime: 60_000,
  });

  const [simPoints, setSimPoints] = useState(10000);
  const [simCpm, setSimCpm] = useState(29.5);
  const [simDest, setSimDest] = useState("Smiles");
  const [simBonus, setSimBonus] = useState(80);

  const target = VPP_TARGETS[simDest] ?? 16;
  const milesObtained = Math.round(simPoints * (1 + simBonus / 100));
  const cpmReal = (simCpm * 1000) / (1000 * (1 + simBonus / 100));
  const totalEconomy = ((target - cpmReal) / 1000) * milesObtained;
  const simClassification = target - cpmReal > 5 ? 'EXCELENTE' : target - cpmReal > 1 ? 'BOM' : target - cpmReal > 0 ? 'NEUTRO' : 'AGUARDAR';

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="accent-line w-10 mb-2" />
        <p className="text-sm text-muted-foreground">Análise de custo efetivo por 1.000 milhas</p>
      </motion.div>

      {/* Banner */}
      <GlassCard accentColor="brand" className="border-l-4" animate delay={0}>
        <p className="text-sm text-foreground leading-relaxed">
          <strong className="text-primary">VPP Real</strong> = custo efetivo para adquirir 1.000 milhas via compra de pontos + transferência bonificada.{" "}
          <strong className="text-primary">Economia/1k</strong> = quanto você paga A MENOS que o valor-alvo. Positivo = vantajoso.
        </p>
      </GlassCard>

      {/* Reference cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KpiCard label="Smiles" value="R$16,00/1k" sub="valor-alvo Melhores Destinos" accent="gold" delay={1} />
        <KpiCard label="Azul Fidelidade" value="R$14,00/1k" sub="valor-alvo Melhores Destinos" accent="purple" delay={2} />
        <KpiCard label="Pass" value="R$14,00/1k" sub="valor-alvo Melhores Destinos" accent="blue" delay={3} />
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-center">
        <select value={dest} onChange={e => setParam("destination", e.target.value)}
          className="glass-card px-4 py-2.5 text-sm bg-transparent text-foreground outline-none focus:ring-1 focus:ring-primary/30 transition-all">
          <option value="">Todos programas</option>
          {Object.keys(VPP_TARGETS).map(p => <option key={p} value={p}>{p}</option>)}
        </select>
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

      {/* Table */}
      {isLoading ? <LoadingState rows={5} /> : error ? <ErrorState onRetry={() => refetch()} /> : data && data.length > 0 ? (
        <GlassCard animate delay={4}>
          <h3 className="text-xs font-heading font-semibold text-muted-foreground mb-4 uppercase tracking-wider flex items-center gap-2">
            VPP por campanha
            <UITooltip>
              <TooltipTrigger><Info className="h-3.5 w-3.5 text-muted-foreground" /></TooltipTrigger>
              <TooltipContent><p className="text-xs">VPP = CPM × paridade ÷ (1 + bônus%)</p></TooltipContent>
            </UITooltip>
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] text-muted-foreground border-b border-border uppercase tracking-wider">
                  <th className="text-left py-3 pr-3">Campanha</th>
                  <th className="text-left py-3 pr-3">Data</th>
                  <th className="text-right py-3 pr-3">Bônus</th>
                  <th className="text-right py-3 pr-3">VPP Base</th>
                  <th className="text-right py-3 pr-3">VPP Clube</th>
                  <th className="text-right py-3 pr-3">VPP Elite</th>
                  <th className="text-right py-3 pr-3">Economia</th>
                  <th className="text-left py-3">Class.</th>
                </tr>
              </thead>
              <tbody>
                {data.map(v => (
                  <tr key={v.campaign_id} className="border-b border-border/50 hover:bg-card/80 transition-colors">
                    <td className="py-3 pr-3 truncate max-w-[180px]">{v.title}</td>
                    <td className="py-3 pr-3 text-muted-foreground text-xs">{v.date}</td>
                    <td className="text-right py-3 pr-3 font-heading font-bold text-primary">{v.bonus_base}→{v.bonus_max}%</td>
                    <td className="text-right py-3 pr-3">R${v.vpp_base.toFixed(2).replace('.', ',')}</td>
                    <td className="text-right py-3 pr-3">{v.vpp_clube != null ? `R$${v.vpp_clube.toFixed(2).replace('.', ',')}` : '—'}</td>
                    <td className="text-right py-3 pr-3">{v.vpp_elite != null ? `R$${v.vpp_elite.toFixed(2).replace('.', ',')}` : '—'}</td>
                    <td className={cn("text-right py-3 pr-3 font-medium", v.economy_per_k >= 0 ? "text-miles-green" : "text-primary")}>R${v.economy_per_k.toFixed(2).replace('.', ',')}</td>
                    <td className="py-3"><OpBadge classification={v.classification} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      ) : (
        <GlassCard className="py-12 text-center text-sm text-muted-foreground">Nenhum dado VPP disponível.</GlassCard>
      )}

      {data && data.length > 0 && (
        <GlassCard animate delay={5}>
          <h3 className="text-xs font-heading font-semibold text-muted-foreground mb-4 uppercase tracking-wider">VPP histórico</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data}>
              <XAxis dataKey="date" tick={{ fill: '#555', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#555', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="vpp_base" stroke="#2C048C" strokeWidth={2} dot={false} name="VPP Base" />
              {dest && VPP_TARGETS[dest] && <ReferenceLine y={VPP_TARGETS[dest]} stroke="#555" strokeDasharray="5 5" label={{ value: 'Alvo', fill: '#888', fontSize: 11 }} />}
            </LineChart>
          </ResponsiveContainer>
        </GlassCard>
      )}

      {/* Simulator */}
      <GlassCard animate delay={6} accentColor="brand" className="border-l-4">
        <div className="flex items-center gap-2 mb-6">
          <div className="h-8 w-8 rounded-lg brand-gradient flex items-center justify-center">
            <Calculator className="h-4 w-4 text-primary-foreground" />
          </div>
          <h3 className="text-sm font-heading font-semibold">Simulador interativo</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="space-y-1.5">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Saldo de pontos (Livelo)</label>
            <input type="number" value={simPoints} onChange={e => setSimPoints(Number(e.target.value))}
              className="glass-card w-full px-4 py-2.5 text-sm bg-transparent text-foreground outline-none focus:ring-1 focus:ring-primary/30 transition-all" />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">CPM origem (R$/1k)</label>
            <input type="number" step="0.5" value={simCpm} onChange={e => setSimCpm(Number(e.target.value))}
              className="glass-card w-full px-4 py-2.5 text-sm bg-transparent text-foreground outline-none focus:ring-1 focus:ring-primary/30 transition-all" />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Programa destino</label>
            <select value={simDest} onChange={e => setSimDest(e.target.value)}
              className="glass-card w-full px-4 py-2.5 text-sm bg-transparent text-foreground outline-none focus:ring-1 focus:ring-primary/30 transition-all">
              {Object.keys(VPP_TARGETS).map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Bônus disponível (%)</label>
            <input type="number" value={simBonus} onChange={e => setSimBonus(Number(e.target.value))}
              className="glass-card w-full px-4 py-2.5 text-sm bg-transparent text-foreground outline-none focus:ring-1 focus:ring-primary/30 transition-all" />
          </div>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard label="Milhas obtidas" value={milesObtained.toLocaleString('pt-BR')} accent="brand" />
          <KpiCard label="CPM real" value={`R$${cpmReal.toFixed(2).replace('.', ',')}/1k`} accent="blue" />
          <KpiCard label="Valor-alvo" value={`R$${target.toFixed(2).replace('.', ',')}/1k`} accent="green" />
          <GlassCard accentColor={totalEconomy >= 0 ? 'green' : 'red'}>
            <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Economia total</span>
            <span className={cn("text-2xl font-heading font-bold block mt-1", totalEconomy >= 0 ? "text-miles-green" : "text-primary")}>
              R${totalEconomy.toFixed(2).replace('.', ',')}
            </span>
            <OpBadge classification={simClassification} className="mt-2" />
          </GlassCard>
        </div>
      </GlassCard>
    </div>
  );
}
