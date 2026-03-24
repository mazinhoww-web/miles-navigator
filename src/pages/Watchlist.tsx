import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Plus, Trash2, Eye, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import type { WatchlistEntry } from "@/types/api";

export default function Watchlist() {
  const qc = useQueryClient();
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [minBonus, setMinBonus] = useState("");
  const [notes, setNotes] = useState("");

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => apiFetch<WatchlistEntry[]>("/api/watchlist"),
    staleTime: 60_000,
  });

  const addMut = useMutation({
    mutationFn: () => apiFetch("/api/watchlist", {
      method: "POST",
      body: JSON.stringify({
        origin: origin || null,
        destination: destination || null,
        min_bonus_pct: minBonus ? Number(minBonus) : null,
        notes: notes || null,
      }),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watchlist"] });
      setOrigin(""); setDestination(""); setMinBonus(""); setNotes("");
      toast.success("Adicionado à watchlist!");
    },
    onError: () => toast.error("Erro ao adicionar."),
  });

  const delMut = useMutation({
    mutationFn: (id: number) => apiFetch(`/api/watchlist/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watchlist"] });
      toast.success("Removido da watchlist.");
    },
    onError: () => toast.error("Erro ao remover."),
  });

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="accent-line w-10 mb-2" />
        <p className="text-sm text-muted-foreground">Monitore rotas e receba alertas de campanhas</p>
      </motion.div>

      {/* Add form */}
      <GlassCard animate delay={0}>
        <div className="flex items-center gap-2 mb-5">
          <div className="h-8 w-8 rounded-lg brand-gradient flex items-center justify-center">
            <Plus className="h-4 w-4 text-primary-foreground" />
          </div>
          <h3 className="text-sm font-heading font-semibold">Adicionar à watchlist</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <div className="space-y-1.5">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Origem</label>
            <input placeholder="ex: Livelo" value={origin} onChange={e => setOrigin(e.target.value)}
              className="glass-card w-full px-4 py-2.5 text-sm bg-transparent text-foreground outline-none focus:ring-1 focus:ring-primary/30 transition-all" />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Destino</label>
            <input placeholder="ex: Smiles" value={destination} onChange={e => setDestination(e.target.value)}
              className="glass-card w-full px-4 py-2.5 text-sm bg-transparent text-foreground outline-none focus:ring-1 focus:ring-primary/30 transition-all" />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Bônus mínimo (%)</label>
            <input placeholder="70" type="number" value={minBonus} onChange={e => setMinBonus(e.target.value)}
              className="glass-card w-full px-4 py-2.5 text-sm bg-transparent text-foreground outline-none focus:ring-1 focus:ring-primary/30 transition-all" />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Notas</label>
            <input placeholder="Observações" value={notes} onChange={e => setNotes(e.target.value)}
              className="glass-card w-full px-4 py-2.5 text-sm bg-transparent text-foreground outline-none focus:ring-1 focus:ring-primary/30 transition-all" />
          </div>
        </div>
        <Button onClick={() => addMut.mutate()} disabled={addMut.isPending} className="gap-2 brand-gradient border-0">
          <Plus className="h-4 w-4" /> Adicionar à watchlist
        </Button>
      </GlassCard>

      {/* List */}
      {isLoading ? <LoadingState rows={3} /> : error ? <ErrorState onRetry={() => refetch()} /> : (
        <div className="space-y-2">
          {!data || data.length === 0 ? (
            <GlassCard className="py-16 text-center">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                <Eye className="h-6 w-6 text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">Sua watchlist está vazia. Adicione rotas para monitorar.</p>
            </GlassCard>
          ) : data.map((entry, i) => (
            <GlassCard key={entry.id} animate delay={i + 1} className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="font-heading font-semibold text-sm flex items-center gap-2">
                  {entry.origin ?? 'Qualquer'}
                  <ArrowRight className="h-3 w-3 text-primary/60" />
                  {entry.destination ?? 'Qualquer'}
                </span>
                {entry.min_bonus_pct != null && (
                  <span className="text-[10px] px-2 py-0.5 rounded-md bg-primary/10 text-primary font-bold tracking-wider border border-primary/20">
                    min: {entry.min_bonus_pct}%
                  </span>
                )}
                {entry.notes && <span className="text-xs text-muted-foreground">{entry.notes}</span>}
              </div>
              <Button variant="ghost" size="icon" onClick={() => delMut.mutate(entry.id)} disabled={delMut.isPending} className="shrink-0 hover:bg-primary/10">
                <Trash2 className="h-4 w-4 text-primary" />
              </Button>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}
