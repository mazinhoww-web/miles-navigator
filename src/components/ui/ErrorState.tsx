import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "./GlassCard";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({ message = "Erro ao carregar dados.", onRetry }: ErrorStateProps) {
  return (
    <GlassCard className="flex flex-col items-center justify-center py-16 gap-4">
      <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
        <AlertTriangle className="h-6 w-6 text-primary" />
      </div>
      <p className="text-muted-foreground text-sm text-center max-w-xs">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="gap-2">
          <RefreshCw className="h-3.5 w-3.5" /> Tentar novamente
        </Button>
      )}
    </GlassCard>
  );
}
