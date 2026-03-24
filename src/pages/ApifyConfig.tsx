import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { GlassCard } from "@/components/ui/GlassCard";
import { KpiCard } from "@/components/ui/KpiCard";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Switch } from "@/components/ui/switch";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  Play, Save, RefreshCw, Settings2, Globe, CheckCircle,
  XCircle, Clock, Loader2, Pencil, Bot
} from "lucide-react";
import { apifyApi } from "@/lib/apify";

type Actor = {
  id: string;
  source_name: string;
  actor_id: string;
  display_name: string;
  description: string | null;
  is_enabled: boolean;
  schedule_minutes: number;
  last_run_id: string | null;
  last_run_status: string | null;
  last_run_at: string | null;
  last_dataset_id: string | null;
  last_items_found: number | null;
  last_new_items: number | null;
};

const statusIcon: Record<string, { icon: typeof CheckCircle; cls: string }> = {
  SUCCEEDED: { icon: CheckCircle, cls: "text-miles-green" },
  FAILED: { icon: XCircle, cls: "text-primary" },
  RUNNING: { icon: Loader2, cls: "text-amber-400 animate-spin" },
  TIMED_OUT: { icon: Clock, cls: "text-amber-400" },
};

export default function ApifyConfig() {
  const qc = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [triggeringId, setTriggeringId] = useState<string | null>(null);

  const { data: actors, isLoading, error, refetch } = useQuery({
    queryKey: ["apify-actors"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("apify_actors")
        .select("*")
        .order("display_name");
      if (error) throw error;
      return data as Actor[];
    },
    staleTime: 30_000,
  });

  const updateMut = useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<Actor> }) => {
      const { error } = await supabase.from("apify_actors").update(updates).eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["apify-actors"] });
      setEditingId(null);
      toast.success("Actor atualizado!");
    },
    onError: () => toast.error("Erro ao atualizar."),
  });

  const toggleEnabled = (actor: Actor) => {
    updateMut.mutate({ id: actor.id, updates: { is_enabled: !actor.is_enabled } });
  };

  const saveActorId = (actor: Actor) => {
    const newActorId = editValues[actor.id] ?? actor.actor_id;
    updateMut.mutate({ id: actor.id, updates: { actor_id: newActorId } });
  };

  const triggerActor = async (actor: Actor) => {
    if (!actor.actor_id) {
      toast.error("Configure o Actor ID primeiro.");
      return;
    }
    setTriggeringId(actor.id);
    try {
      const res = await apifyApi.run(actor.actor_id);
      if (res.success && res.data?.data?.id) {
        await supabase.from("apify_actors").update({
          last_run_id: res.data.data.id,
          last_run_status: "RUNNING",
          last_run_at: new Date().toISOString(),
        }).eq("id", actor.id);
        qc.invalidateQueries({ queryKey: ["apify-actors"] });
        toast.success(`Actor ${actor.display_name} disparado!`);
      } else {
        toast.error(res.error ?? "Erro ao disparar actor.");
      }
    } catch {
      toast.error("Erro de conexão com Apify.");
    } finally {
      setTriggeringId(null);
    }
  };

  const refreshStatus = async (actor: Actor) => {
    if (!actor.last_run_id) return;
    try {
      const res = await apifyApi.getRunStatus(actor.last_run_id);
      if (res.success && res.data?.data) {
        const run = res.data.data;
        await supabase.from("apify_actors").update({
          last_run_status: run.status,
          last_dataset_id: run.defaultDatasetId ?? null,
          last_items_found: run.stats?.datasetItemCount ?? 0,
        }).eq("id", actor.id);
        qc.invalidateQueries({ queryKey: ["apify-actors"] });
        toast.success(`Status atualizado: ${run.status}`);
      }
    } catch {
      toast.error("Erro ao buscar status.");
    }
  };

  const configured = actors?.filter(a => a.actor_id).length ?? 0;
  const enabled = actors?.filter(a => a.is_enabled).length ?? 0;
  const running = actors?.filter(a => a.last_run_status === "RUNNING").length ?? 0;

  if (isLoading) return <LoadingState rows={6} />;
  if (error) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="accent-line w-10 mb-2" />
        <p className="text-sm text-muted-foreground">Gerencie os 14 Actors Apify para scraping de campanhas de milhas</p>
      </motion.div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total fontes" value={actors?.length ?? 0} accent="brand" icon={<Globe className="h-4 w-4" />} delay={0} />
        <KpiCard label="Configurados" value={configured} sub={`${actors?.length ? Math.round(configured / actors.length * 100) : 0}%`} accent="green" icon={<Settings2 className="h-4 w-4" />} delay={1} />
        <KpiCard label="Ativos" value={enabled} accent="blue" icon={<Bot className="h-4 w-4" />} delay={2} />
        <KpiCard label="Rodando" value={running} accent={running > 0 ? "gold" : "purple"} icon={<Play className="h-4 w-4" />} delay={3} />
      </div>

      {/* Actors list */}
      <div className="space-y-3">
        {actors?.map((actor, i) => {
          const isEditing = editingId === actor.id;
          const st = statusIcon[actor.last_run_status ?? ""] ?? null;
          const hasActorId = !!actor.actor_id;

          return (
            <GlassCard key={actor.id} animate delay={i + 4} className="space-y-3">
              {/* Header row */}
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <Switch
                    checked={actor.is_enabled}
                    onCheckedChange={() => toggleEnabled(actor)}
                  />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-heading font-semibold text-sm">{actor.display_name}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-md bg-secondary text-muted-foreground font-mono">
                        {actor.source_name}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{actor.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {st && (() => {
                    const Icon = st.icon;
                    return <Icon className={cn("h-4 w-4", st.cls)} />;
                  })()}
                  {actor.last_run_at && (
                    <span className="text-[10px] text-muted-foreground hidden md:inline">
                      {formatDistanceToNow(new Date(actor.last_run_at), { addSuffix: true, locale: ptBR })}
                    </span>
                  )}
                </div>
              </div>

              {/* Actor ID row */}
              <div className="flex items-center gap-2">
                {isEditing ? (
                  <>
                    <input
                      value={editValues[actor.id] ?? actor.actor_id}
                      onChange={e => setEditValues(v => ({ ...v, [actor.id]: e.target.value }))}
                      placeholder="username/actor-name"
                      className="glass-card flex-1 px-3 py-2 text-sm bg-transparent text-foreground outline-none focus:ring-1 focus:ring-primary/30 transition-all font-mono"
                    />
                    <Button size="sm" onClick={() => saveActorId(actor)} disabled={updateMut.isPending} className="gap-1 brand-gradient border-0">
                      <Save className="h-3.5 w-3.5" /> Salvar
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>Cancelar</Button>
                  </>
                ) : (
                  <>
                    <code className={cn("text-xs px-3 py-2 rounded-lg flex-1 truncate",
                      hasActorId ? "bg-secondary/50 text-foreground" : "bg-primary/5 text-muted-foreground italic"
                    )}>
                      {hasActorId ? actor.actor_id : "Actor ID não configurado"}
                    </code>
                    <Button size="sm" variant="ghost" onClick={() => { setEditingId(actor.id); setEditValues(v => ({ ...v, [actor.id]: actor.actor_id })); }} className="gap-1">
                      <Pencil className="h-3.5 w-3.5" /> Editar
                    </Button>
                  </>
                )}
              </div>

              {/* Actions row */}
              <div className="flex items-center gap-2 flex-wrap">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => triggerActor(actor)}
                  disabled={!hasActorId || triggeringId === actor.id || !actor.is_enabled}
                  className="gap-1.5"
                >
                  {triggeringId === actor.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                  Executar
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => refreshStatus(actor)}
                  disabled={!actor.last_run_id}
                  className="gap-1.5"
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Atualizar status
                </Button>
                {actor.last_items_found != null && actor.last_items_found > 0 && (
                  <span className="text-xs text-muted-foreground ml-auto">
                    {actor.last_items_found} encontradas • {actor.last_new_items ?? 0} novas
                  </span>
                )}
              </div>

              {/* Config progress */}
              {hasActorId && (
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Intervalo: {actor.schedule_minutes}min</span>
                  <Progress value={hasActorId ? 100 : 0} className="flex-1 h-1" />
                </div>
              )}
            </GlassCard>
          );
        })}
      </div>
    </div>
  );
}
