import { cn } from "@/lib/utils";

interface OpBadgeProps {
  vppReal?: number | null;
  vppTarget?: number | null;
  classification?: string;
  className?: string;
}

export function OpBadge({ vppReal, vppTarget, classification, className }: OpBadgeProps) {
  const economy = vppTarget != null && vppReal != null ? vppTarget - vppReal : null;
  const label = classification
    ? classification.toUpperCase()
    : economy === null ? '—'
    : economy > 5 ? 'EXCELENTE'
    : economy > 1 ? 'BOM'
    : economy > 0 ? 'NEUTRO'
    : 'AGUARDAR';
  const cls = label === 'EXCELENTE' ? 'bg-emerald-500/12 text-emerald-400 border-emerald-500/20'
            : label === 'BOM'       ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
            : label === 'NEUTRO'    ? 'bg-secondary text-muted-foreground border-border'
            : label === 'AGUARDAR'  ? 'bg-primary/12 text-primary border-primary/20'
            : 'bg-secondary text-muted-foreground border-border';
  return <span className={cn("text-[10px] px-2.5 py-1 rounded-md font-bold tracking-wider border", cls, className)}>{label}</span>;
}
