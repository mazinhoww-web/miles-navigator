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
import { Activity, Server, Play } from "lucide-react";
import { toast } from "sonner";
import type { HealthResponse } from "@/types/api";

const statusColors: Record<string, string> = {
  ok: "bg-miles-green",
  error: "bg-miles-red",
  never_run: "bg-gray-500",
  running: "bg-yellow-400 animate-pulse",
};

const globalStatusMap: Record<string, { label: string; cls: string }> = {
  ok: { label: "OK", cls: "bg-green-500/15 text-green-400" },
  degraded: { label: "DEGRADADO", cls: "bg-yellow-500/15 text-yellow-400" },
  error: { label: "ERRO", cls: "bg-red-500/15 text-red-400" },
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
    <div className="space-y-6">
      {/* Global status */}
      <div className="flex items-center gap-4 flex-wrap">
        <span className={cn("text-sm px-4 py-1.5 rounded-full font-heading font-bold", gs.cls)}>{gs.label}</span>
        <Button onClick={() => triggerMut.mutate()} disabled={triggerMut.isPending} size="sm" className="gap-2">
          <Play className="h-4 w-4" /> Disparar scraping manual
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <KpiCard label="Total campanhas" value={data.total_campaigns} accent="gold" icon={<Activity className="h-4 w-4" />} />
        <KpiCard label="Ativas agora" value={data.active_now} accent="green" icon={<Server className="h-4 w-4" />} />
        <KpiCard label="Este mês" value={data.this_month} accent="blue" />
      </div>

      {/* Scrapers table */}
      <GlassCard>
        <h3 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Scrapers ({data.scrapers_ok} ok / {data.scrapers_error} erro)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-muted-foreground border-b border-border">
                <th className="text-left py-2 pr-3">Fonte</th>
                <th className="text-left py-2 pr-3">Último run</th>
                <th className="text-center py-2 pr-3">Status</th>
                <th className="text-right py-2 pr-3">Encontradas</th>
                <th className="text-right py-2 pr-3">Novas</th>
                <th className="text-right py-2 pr-3">Duração</th>
                <th className="text-center py-2">Bootstrap</th>
              </tr>
            </thead>
            <tbody>
              {data.scrapers.map(s => (
                <tr key={s.name} className="border-b border-border/50 hover:bg-white/[0.02]">
                  <td className="py-2 pr-3 font-medium">{s.name}</td>
                  <td className="py-2 pr-3 text-xs text-muted-foreground">
                    {s.last_run ? formatDistanceToNow(new Date(s.last_run), { addSuffix: true, locale: ptBR }) : '—'}
                  </td>
                  <td className="py-2 pr-3 text-center">
                    <span className="flex items-center justify-center gap-1.5">
                      <span className={cn("h-2 w-2 rounded-full", statusColors[s.last_status] ?? "bg-gray-500")} />
                      <span className="text-xs">{s.last_status}</span>
                    </span>
                  </td>
                  <td className="text-right py-2 pr-3">{s.last_found}</td>
                  <td className="text-right py-2 pr-3">{s.last_new}</td>
                  <td className="text-right py-2 pr-3 text-muted-foreground">{s.duration_s != null ? `${s.duration_s.toFixed(1)}s` : '—'}</td>
                  <td className="py-2 text-center">
                    <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium",
                      s.bootstrap_complete ? "bg-green-500/15 text-green-400" : "bg-yellow-500/15 text-yellow-400"
                    )}>
                      {s.bootstrap_complete ? "✓" : `${s.bootstrap_pages}pg`}
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
