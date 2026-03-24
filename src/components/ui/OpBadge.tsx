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
  const cls = label === 'EXCELENTE' ? 'bg-green-500/15 text-green-400'
            : label === 'BOM'       ? 'bg-blue-500/12 text-blue-400'
            : label === 'NEUTRO'    ? 'bg-gray-500/15 text-gray-400'
            : label === 'AGUARDAR'  ? 'bg-red-500/15 text-red-400'
            : 'bg-gray-500/15 text-gray-400';
  return <span className={cn("text-xs px-2 py-0.5 rounded-full font-semibold", cls, className)}>{label}</span>;
}
