import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { KpiCard } from "@/components/ui/KpiCard";
import { ProgramPill } from "@/components/ui/ProgramPill";
import { OpBadge } from "@/components/ui/OpBadge";
import { CampaignCard } from "@/components/ui/CampaignCard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Progress } from "@/components/ui/progress";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { ChevronRight } from "lucide-react";
import type { Campaign, BonusTier } from "@/types/api";

const VPP_TARGETS: Record<string, number> = { smiles: 16, 'latam pass': 25, azul: 14 };

export default function CampaignDetail() {
  const { id } = useParams();
  const { data: campaign, isLoading, error, refetch } = useQuery({
    queryKey: ["campaign", id],
    queryFn: () => apiFetch<Campaign>(`/api/promos/${id}`),
    staleTime: 60_000,
  });

  const { data: vppData } = useQuery({
    queryKey: ["vpp-campaign", id],
    queryFn: () => apiFetch<BonusTier[]>(`/api/vpp/campaign/${id}`),
    staleTime: 60_000,
    enabled: !!id,
  });

  const { data: similar } = useQuery({
    queryKey: ["similar", id],
    queryFn: () => apiFetch<Campaign[]>(`/api/promos/${id}/similar`),
    staleTime: 60_000,
    enabled: !!id,
  });

  if (isLoading) return <LoadingState rows={6} />;
  if (error || !campaign) return <ErrorState onRetry={() => refetch()} />;

  const c = campaign;
  const target = c.destination_program ? VPP_TARGETS[c.destination_program.toLowerCase()] : undefined;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Link to="/" className="hover:text-foreground transition-colors">Monitor</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-foreground">Detalhe</span>
      </div>

      {/* Header */}
      <div>
        <h2 className="text-xl font-heading font-bold">{c.title}</h2>
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          {c.origin_program && <ProgramPill name={c.origin_program} />}
          {c.destination_program && <ProgramPill name={c.destination_program} />}
          {c.starts_at && <span className="text-xs text-muted-foreground">Início: {format(new Date(c.starts_at), "dd/MM/yyyy HH:mm", { locale: ptBR })}</span>}
          {c.ends_at && <span className="text-xs text-muted-foreground">Fim: {format(new Date(c.ends_at), "dd/MM/yyyy HH:mm", { locale: ptBR })}</span>}
        </div>
      </div>

      {/* Highlight cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KpiCard label="Bônus máximo" value={c.bonus_pct_max != null ? `${c.bonus_pct_max}%` : '—'} accent="gold" />
        <KpiCard label="CPM mínimo" value={c.cpm_min != null ? `R$${c.cpm_min.toFixed(2).replace('.', ',')}/1k` : '—'} accent="green" />
        <GlassCard accentColor="blue" className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Classificação</span>
          <OpBadge vppReal={c.vpp_real_base} vppTarget={target} className="text-base mt-1 w-fit" />
          {target && c.vpp_real_base != null && (
            <span className="text-xs text-muted-foreground">Economia: R${(target - c.vpp_real_base).toFixed(2).replace('.', ',')}/1k</span>
          )}
        </GlassCard>
      </div>

      {/* Bonus tiers table */}
      {(vppData ?? c.bonus_tiers)?.length > 0 && (
        <GlassCard>
          <h3 className="text-sm font-heading font-semibold mb-3">Tiers de Bônus</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-muted-foreground border-b border-border">
                  <th className="text-left py-2 pr-4">Perfil</th>
                  <th className="text-right py-2 pr-4">Bônus %</th>
                  <th className="text-right py-2 pr-4">VPP Real</th>
                  <th className="text-right py-2 pr-4">Economia</th>
                  <th className="text-left py-2">Classificação</th>
                </tr>
              </thead>
              <tbody>
                {(vppData ?? c.bonus_tiers).map((t) => (
                  <tr key={t.id} className="border-b border-border/50">
                    <td className="py-2 pr-4 font-medium">{t.tier_name}</td>
                    <td className="text-right py-2 pr-4">
                      <div className="flex items-center gap-2 justify-end">
                        <span>{t.bonus_pct}%</span>
                        <Progress value={Math.min(t.bonus_pct / 1.5, 100)} className="w-16 h-1.5" />
                      </div>
                    </td>
                    <td className="text-right py-2 pr-4 text-miles-green">{t.vpp_real != null ? `R$${t.vpp_real.toFixed(2).replace('.', ',')}` : '—'}</td>
                    <td className="text-right py-2 pr-4">{t.economy_per_k != null ? `R$${t.economy_per_k.toFixed(2).replace('.', ',')}` : '—'}</td>
                    <td className="py-2"><OpBadge classification={t.classification} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}

      {/* Loyalty tiers */}
      {c.loyalty_tiers?.length > 0 && (
        <GlassCard>
          <h3 className="text-sm font-heading font-semibold mb-3">Tiers de Fidelidade</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-muted-foreground border-b border-border">
                  <th className="text-left py-2 pr-4">Tempo no clube</th>
                  <th className="text-right py-2 pr-4">Bônus extra</th>
                  <th className="text-right py-2">Bônus total</th>
                </tr>
              </thead>
              <tbody>
                {c.loyalty_tiers.map((t) => (
                  <tr key={t.id} className="border-b border-border/50">
                    <td className="py-2 pr-4">{t.label}</td>
                    <td className="text-right py-2 pr-4">+{t.bonus_pct_extra}%</td>
                    <td className="text-right py-2 font-heading font-bold text-primary">{(c.bonus_pct_base ?? 0) + t.bonus_pct_extra}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}

      {/* Similar */}
      {similar && similar.length > 0 && (
        <div>
          <h3 className="text-sm font-heading font-semibold text-muted-foreground mb-3">Campanhas similares</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {similar.slice(0, 4).map(s => <CampaignCard key={s.id} campaign={s} compact />)}
          </div>
        </div>
      )}

      {/* Raw text */}
      {c.raw_text && (
        <Accordion type="single" collapsible>
          <AccordionItem value="raw">
            <AccordionTrigger className="text-sm font-heading">Texto bruto da campanha</AccordionTrigger>
            <AccordionContent>
              <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-body">{c.raw_text}</pre>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )}
    </div>
  );
}
