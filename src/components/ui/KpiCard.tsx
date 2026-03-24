import { GlassCard } from "./GlassCard";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface KpiCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: 'gold' | 'green' | 'blue' | 'red' | 'purple';
  icon?: ReactNode;
}

export function KpiCard({ label, value, sub, accent = 'gold', icon }: KpiCardProps) {
  return (
    <GlassCard accentColor={accent} className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{label}</span>
        {icon && <span className="text-muted-foreground">{icon}</span>}
      </div>
      <span className={cn("text-2xl font-heading font-bold", 
        accent === 'gold' ? 'text-primary' : 
        accent === 'green' ? 'text-miles-green' : 
        accent === 'blue' ? 'text-miles-blue' : 
        accent === 'red' ? 'text-miles-red' : 'text-miles-purple'
      )}>{value}</span>
      {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
    </GlassCard>
  );
}
