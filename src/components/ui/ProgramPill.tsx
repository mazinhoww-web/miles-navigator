import { cn } from "@/lib/utils";

interface ProgramPillProps {
  name: string;
  className?: string;
}

export function ProgramPill({ name, className }: ProgramPillProps) {
  const n = name?.toLowerCase() ?? '';
  const cls = n.includes('smiles')  ? 'bg-amber-500/12 text-amber-400 border border-amber-500/20'
            : n.includes('azul')    ? 'bg-blue-500/12 text-blue-400 border border-blue-500/20'
            : n.includes('pass')    ? 'bg-purple-500/12 text-purple-400 border border-purple-500/20'
            : n.includes('livelo')  ? 'bg-rose-500/12 text-rose-400 border border-rose-500/20'
            : n.includes('esfera')  ? 'bg-emerald-500/12 text-emerald-400 border border-emerald-500/20'
            : 'bg-secondary text-muted-foreground border border-border';
  return <span className={cn("text-[10px] px-2 py-0.5 rounded-md font-semibold tracking-wide uppercase", cls, className)}>{name}</span>;
}
