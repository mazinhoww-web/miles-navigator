import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
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
    <div className="space-y-6">
      {/* Add form */}
      <GlassCard>
        <h3 className="text-sm font-heading font-semibold text-muted-foreground mb-4">Adicionar à watchlist</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <input placeholder="Origem (ex: Livelo)" value={origin} onChange={e => setOrigin(e.target.value)}
            className="glass-card px-3 py-2 text-sm bg-transparent text-foreground outline-none" />
          <input placeholder="Destino (ex: Smiles)" value={destination} onChange={e => setDestination(e.target.value)}
            className="glass-card px-3 py-2 text-sm bg-transparent text-foreground outline-none" />
          <input placeholder="Bônus mínimo (%)" type="number" value={minBonus} onChange={e => setMinBonus(e.target.value)}
            className="glass-card px-3 py-2 text-sm bg-transparent text-foreground outline-none" />
          <input placeholder="Notas" value={notes} onChange={e => setNotes(e.target.value)}
            className="glass-card px-3 py-2 text-sm bg-transparent text-foreground outline-none" />
        </div>
        <Button onClick={() => addMut.mutate()} disabled={addMut.isPending} className="gap-2">
          <Plus className="h-4 w-4" /> Adicionar à watchlist
        </Button>
      </GlassCard>

      {/* List */}
      {isLoading ? <LoadingState rows={3} /> : error ? <ErrorState onRetry={() => refetch()} /> : (
        <div className="space-y-2">
          {!data || data.length === 0 ? (
            <GlassCard className="py-8 text-center text-sm text-muted-foreground">
              Sua watchlist está vazia. Adicione rotas para monitorar.
            </GlassCard>
          ) : data.map(entry => (
            <GlassCard key={entry.id} className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="font-heading font-semibold text-sm">
                  {entry.origin ?? 'Qualquer'} → {entry.destination ?? 'Qualquer'}
                </span>
                {entry.min_bonus_pct != null && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                    min: {entry.min_bonus_pct}%
                  </span>
                )}
                {entry.notes && <span className="text-xs text-muted-foreground">{entry.notes}</span>}
              </div>
              <Button variant="ghost" size="icon" onClick={() => delMut.mutate(entry.id)} disabled={delMut.isPending}>
                <Trash2 className="h-4 w-4 text-miles-red" />
              </Button>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}
