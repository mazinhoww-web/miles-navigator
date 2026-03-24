import { cn } from "@/lib/utils";

interface ProgramPillProps {
  name: string;
  className?: string;
}

export function ProgramPill({ name, className }: ProgramPillProps) {
  const n = name?.toLowerCase() ?? '';
  const cls = n.includes('smiles')  ? 'bg-yellow-100 text-yellow-900'
            : n.includes('latam')   ? 'bg-blue-100 text-blue-900'
            : n.includes('azul')    ? 'bg-purple-100 text-purple-900'
            : n.includes('livelo')  ? 'bg-rose-100 text-rose-900'
            : n.includes('esfera')  ? 'bg-green-100 text-green-900'
            : 'bg-muted text-muted-foreground';
  return <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", cls, className)}>{name}</span>;
}
