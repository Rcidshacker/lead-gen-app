import React from 'react';
import { cn } from '@/lib/utils';

// ─── Variant Map ───
const variantStyles = {
  default: 'bg-slate-100 text-slate-700',
  primary: 'bg-primary-100 text-primary-700',
  success: 'bg-emerald-100 text-emerald-700',
  warning: 'bg-amber-100 text-amber-700',
  danger: 'bg-red-100 text-red-700',
  info: 'bg-blue-100 text-blue-700',
};

// ─── Props ───
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: keyof typeof variantStyles;
  size?: 'sm' | 'md';
  dot?: boolean;
}

// ─── Component ───
export function Badge({
  className,
  variant = 'default',
  size = 'sm',
  dot = false,
  children,
  ...props
}: BadgeProps) {
  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-medium rounded-full whitespace-nowrap',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {dot && (
        <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      )}
      {children}
    </span>
  );
}

// ─── Convenience Status Badge ───
export interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

const statusVariantMap: Record<string, keyof typeof variantStyles> = {
  new: 'info',
  contacted: 'warning',
  interested: 'success',
  rejected: 'danger',
  hired: 'primary',
  active: 'success',
  paused: 'warning',
  error: 'danger',
  pending: 'default',
  running: 'primary',
  completed: 'success',
  failed: 'danger',
  cancelled: 'warning',
};

export function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  return (
    <Badge variant={statusVariantMap[status] || 'default'} size={size} dot>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

export default Badge;
