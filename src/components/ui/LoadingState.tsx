import { Skeleton } from "@/components/ui/skeleton";

export function LoadingState({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="glass-card p-5 space-y-3">
          <Skeleton className="h-4 w-3/4 shimmer rounded-md" />
          <Skeleton className="h-3 w-1/2 shimmer rounded-md" />
        </div>
      ))}
    </div>
  );
}

export function LoadingKpis({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass-card p-5 space-y-3">
          <Skeleton className="h-3 w-20 shimmer rounded-md" />
          <Skeleton className="h-8 w-16 shimmer rounded-md" />
          <Skeleton className="h-3 w-24 shimmer rounded-md" />
        </div>
      ))}
    </div>
  );
}
