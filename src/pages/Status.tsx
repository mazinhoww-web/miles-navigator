import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { KpiCard } from "@/components/ui/KpiCard";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Activity, Server, Play, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import type { HealthResponse } from "@/types/api";

const statusColors: Record<string, string> = {
  ok: "bg-miles-green",
  error: "bg-primary",
  never_run: "bg-muted-foreground/50",
  running: "bg-amber-400 animate-pulse-soft",
};

const globalStatusMap: Record<string, { label: string; cls: string }> = {
  ok: { label: "OPERACIONAL", cls: "bg-emerald-500/12 text-emerald-400 border-emerald-500/20" },
  degraded: { label: "DEGRADADO", cls: "bg-amber-500/12 text-amber-400 border-amber-500/20" },
  error: { label: "ERRO", cls: "bg-primary/15 text-primary border-primary/20" },
};

export default function Status() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<HealthResponse>("/api/health"),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const triggerMut = useMutation({
    mutationFn: () => apiFetch("/api/scrape/trigger", { method: "POST" }),
    onSuccess: () => { toast.success("Scraping disparado!"); refetch(); },
    onError: () => toast.error("Erro ao disparar scraping."),
  });

  if (isLoading) return <LoadingState rows={6} />;
  if (error || !data) return <ErrorState onRetry={() => refetch()} />;

  const gs = globalStatusMap[data.status] ?? globalStatusMap.error;

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="accent-line w-10 mb-2" />
        <p className="text-sm text-muted-foreground">Monitoramento dos scrapers e integridade do sistema</p>
      </motion.div>

      {/* Global status */}
      <div className="flex items-center gap-4 flex-wrap">
        <span className={cn("text-[10px] px-4 py-2 rounded-md font-heading font-bold tracking-wider border", gs.cls)}>{gs.label}</span>
        <Button onClick={() => triggerMut.mutate()} disabled={triggerMut.isPending} size="sm" className="gap-2 brand-gradient border-0">
          <Play className="h-4 w-4" /> Disparar scraping manual
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <KpiCard label="Total campanhas" value={data.total_campaigns} accent="brand" icon={<Activity className="h-4 w-4" />} delay={0} />
        <KpiCard label="Ativas agora" value={data.active_now} accent="green" icon={<Server className="h-4 w-4" />} delay={1} />
        <KpiCard label="Este mês" value={data.this_month} accent="blue" delay={2} />
      </div>

      {/* Scrapers table */}
      <GlassCard animate delay={3}>
        <h3 className="text-xs font-heading font-semibold text-muted-foreground mb-4 uppercase tracking-wider">
          Scrapers ({data.scrapers_ok} ok / {data.scrapers_error} erro)
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] text-muted-foreground border-b border-border uppercase tracking-wider">
                <th className="text-left py-3 pr-3">Fonte</th>
                <th className="text-left py-3 pr-3">Último run</th>
                <th className="text-center py-3 pr-3">Status</th>
                <th className="text-right py-3 pr-3">Encontradas</th>
                <th className="text-right py-3 pr-3">Novas</th>
                <th className="text-right py-3 pr-3">Duração</th>
                <th className="text-center py-3">Bootstrap</th>
              </tr>
            </thead>
            <tbody>
              {data.scrapers.map(s => (
                <tr key={s.name} className="border-b border-border/50 hover:bg-card/80 transition-colors">
                  <td className="py-3 pr-3 font-medium">{s.name}</td>
                  <td className="py-3 pr-3 text-xs text-muted-foreground">
                    {s.last_run ? formatDistanceToNow(new Date(s.last_run), { addSuffix: true, locale: ptBR }) : '—'}
                  </td>
                  <td className="py-3 pr-3 text-center">
                    <span className="flex items-center justify-center gap-1.5">
                      <span className={cn("h-2 w-2 rounded-full", statusColors[s.last_status] ?? "bg-muted-foreground/50")} />
                      <span className="text-xs">{s.last_status}</span>
                    </span>
                  </td>
                  <td className="text-right py-3 pr-3">{s.last_found}</td>
                  <td className="text-right py-3 pr-3">{s.last_new}</td>
                  <td className="text-right py-3 pr-3 text-muted-foreground">{s.duration_s != null ? `${s.duration_s.toFixed(1)}s` : '—'}</td>
                  <td className="py-3 text-center">
                    <span className={cn("text-[10px] px-2 py-0.5 rounded-md font-medium border",
                      s.bootstrap_complete
                        ? "bg-emerald-500/12 text-emerald-400 border-emerald-500/20"
                        : "bg-amber-500/12 text-amber-400 border-amber-500/20"
                    )}>
                      {s.bootstrap_complete ? <CheckCircle className="h-3 w-3 inline" /> : `${s.bootstrap_pages}pg`}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}
