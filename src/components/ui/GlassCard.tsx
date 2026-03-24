import { cn } from "@/lib/utils";
import { ReactNode } from "react";
import { motion } from "framer-motion";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  accentColor?: 'gold' | 'green' | 'blue' | 'red' | 'purple' | 'brand';
  flash?: boolean;
  onClick?: () => void;
  animate?: boolean;
  delay?: number;
}

const accentMap = {
  gold: 'border-l-amber-500',
  green: 'border-l-emerald-500',
  blue: 'border-l-blue-500',
  red: 'border-l-red-500',
  purple: 'border-l-purple-500',
  brand: 'border-l-primary',
};

export function GlassCard({ children, className, accentColor, flash, onClick, animate = false, delay = 0 }: GlassCardProps) {
  const content = (
    <div
      onClick={onClick}
      className={cn(
        "glass-card p-5",
        accentColor && `border-l-[3px] ${accentMap[accentColor]}`,
        flash && "flash-pulse",
        onClick && "cursor-pointer hover:bg-card/80 transition-all duration-200 hover:shadow-lg hover:shadow-brand-indigo/5",
        className
      )}
    >
      {children}
    </div>
  );

  if (animate) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: delay * 0.08, ease: "easeOut" }}
      >
        {content}
      </motion.div>
    );
  }

  return content;
}
