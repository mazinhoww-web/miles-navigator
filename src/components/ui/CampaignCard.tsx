import { useNavigate } from "react-router-dom";
import { GlassCard } from "./GlassCard";
import { ProgramPill } from "./ProgramPill";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Zap, ArrowRight, Clock } from "lucide-react";
import type { Campaign } from "@/types/api";

interface CampaignCardProps {
  campaign: Campaign;
  compact?: boolean;
  delay?: number;
}

const typeLabels: Record<string, string> = {
  transfer_bonus: 'Bônus Transferência',
  direct_purchase: 'Compra Direta',
  club_combo: 'Clube + Combo',
  flash_sale: 'Flash Sale',
  club_signup: 'Assinatura Clube',
  other: 'Outro',
};

export function CampaignCard({ campaign, compact, delay = 0 }: CampaignCardProps) {
  const navigate = useNavigate();
  const c = campaign;

  return (
    <GlassCard
      flash={c.is_flash}
      onClick={() => navigate(`/campanha/${c.id}`)}
      className={compact ? "py-3" : ""}
      animate
      delay={delay}
    >
      <div className="flex items-center gap-2 flex-wrap mb-2">
        {c.destination_program && <ProgramPill name={c.destination_program} />}
        <span className="text-[10px] px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground font-medium">
          {typeLabels[c.promo_type] ?? c.promo_type}
        </span>
        {c.is_flash && (
          <span className="text-[10px] px-2 py-0.5 rounded-md bg-primary/15 text-primary font-semibold flex items-center gap-1">
            <Zap className="h-3 w-3" /> Flash
          </span>
        )}
      </div>
      <p className="text-sm font-medium text-foreground truncate">{c.title}</p>
      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground flex-wrap">
        {c.origin_program && (
          <span className="flex items-center gap-1">
            {c.origin_program} <ArrowRight className="h-3 w-3 text-primary/60" /> {c.destination_program}
          </span>
        )}
        {c.ends_at && (
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {format(new Date(c.ends_at), "dd/MM HH:mm", { locale: ptBR })}
          </span>
        )}
        {c.cpm_min != null && (
          <span className="text-miles-green font-medium">R${c.cpm_min.toFixed(2).replace('.', ',')}/1k</span>
        )}
        {c.bonus_pct_max != null && (
          <span className="text-primary font-heading font-bold text-lg ml-auto">
            {c.bonus_pct_max}%
          </span>
        )}
      </div>
    </GlassCard>
  );
}
