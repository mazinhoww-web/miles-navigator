import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  accentColor?: 'gold' | 'green' | 'blue' | 'red' | 'purple';
  flash?: boolean;
  onClick?: () => void;
}

const accentMap = {
  gold: 'border-l-amber-500',
  green: 'border-l-emerald-500',
  blue: 'border-l-blue-500',
  red: 'border-l-red-500',
  purple: 'border-l-purple-500',
};

export function GlassCard({ children, className, accentColor, flash, onClick }: GlassCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "glass-card p-4",
        accentColor && `border-l-2 ${accentMap[accentColor]}`,
        flash && "flash-pulse",
        onClick && "cursor-pointer hover:bg-white/[0.06] transition-colors",
        className
      )}
    >
      {children}
    </div>
  );
}
