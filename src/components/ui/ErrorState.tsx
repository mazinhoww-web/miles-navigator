import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "./GlassCard";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({ message = "Erro ao carregar dados.", onRetry }: ErrorStateProps) {
  return (
    <GlassCard className="flex flex-col items-center justify-center py-12 gap-4">
      <AlertTriangle className="h-10 w-10 text-miles-red" />
      <p className="text-muted-foreground text-sm">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Tentar novamente
        </Button>
      )}
    </GlassCard>
  );
}
