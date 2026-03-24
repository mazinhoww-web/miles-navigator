import { useNavigate } from "react-router-dom";
import { GlassCard } from "./GlassCard";
import { ProgramPill } from "./ProgramPill";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Zap } from "lucide-react";
import type { Campaign } from "@/types/api";

interface CampaignCardProps {
  campaign: Campaign;
  compact?: boolean;
}

const typeLabels: Record<string, string> = {
  transfer_bonus: 'Bônus Transferência',
  direct_purchase: 'Compra Direta',
  club_combo: 'Clube + Combo',
  flash_sale: 'Flash Sale',
  club_signup: 'Assinatura Clube',
  other: 'Outro',
};

export function CampaignCard({ campaign, compact }: CampaignCardProps) {
  const navigate = useNavigate();
  const c = campaign;

  return (
    <GlassCard
      flash={c.is_flash}
      onClick={() => navigate(`/campanha/${c.id}`)}
      className={compact ? "py-3" : ""}
    >
      <div className="flex items-center gap-2 flex-wrap mb-1">
        {c.destination_program && <ProgramPill name={c.destination_program} />}
        <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground font-medium">
          {typeLabels[c.promo_type] ?? c.promo_type}
        </span>
        {c.is_flash && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 font-semibold flex items-center gap-1">
            <Zap className="h-3 w-3" /> Flash
          </span>
        )}
      </div>
      <p className="text-sm font-medium text-foreground truncate mt-1">{c.title}</p>
      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground flex-wrap">
        {c.origin_program && <span>De: {c.origin_program}</span>}
        {c.ends_at && (
          <span>até {format(new Date(c.ends_at), "dd/MM HH:mm", { locale: ptBR })}</span>
        )}
        {c.cpm_min != null && (
          <span className="text-miles-green font-medium">CPM R${c.cpm_min.toFixed(2).replace('.', ',')}/1k</span>
        )}
        {c.bonus_pct_max != null && (
          <span className="text-primary font-heading font-bold text-base ml-auto">
            {c.bonus_pct_max}%
          </span>
        )}
      </div>
    </GlassCard>
  );
}
