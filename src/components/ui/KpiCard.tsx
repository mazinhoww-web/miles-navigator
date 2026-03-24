import { GlassCard } from "./GlassCard";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface KpiCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: 'gold' | 'green' | 'blue' | 'red' | 'purple' | 'brand';
  icon?: ReactNode;
  delay?: number;
}

export function KpiCard({ label, value, sub, accent = 'brand', icon, delay = 0 }: KpiCardProps) {
  return (
    <GlassCard accentColor={accent} className="flex flex-col gap-1.5" animate delay={delay}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">{label}</span>
        {icon && <span className="text-muted-foreground opacity-60">{icon}</span>}
      </div>
      <span className={cn("text-2xl font-heading font-bold tracking-tight",
        accent === 'gold' ? 'text-gold' :
        accent === 'green' ? 'text-miles-green' :
        accent === 'blue' ? 'text-miles-blue' :
        accent === 'red' || accent === 'brand' ? 'text-primary' :
        'text-miles-purple'
      )}>{value}</span>
      {sub && <span className="text-[11px] text-muted-foreground leading-tight">{sub}</span>}
    </GlassCard>
  );
}
