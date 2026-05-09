import React, { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Variant & Size Maps ───
const variantStyles = {
  primary: [
    'bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800',
    'focus-visible:ring-primary-500',
    'shadow-sm',
  ].join(' '),
  secondary: [
    'bg-secondary-100 text-secondary-700 hover:bg-secondary-200 active:bg-secondary-300',
    'focus-visible:ring-secondary-400',
  ].join(' '),
  danger: [
    'bg-red-600 text-white hover:bg-red-700 active:bg-red-800',
    'focus-visible:ring-red-500',
    'shadow-sm',
  ].join(' '),
  ghost: [
    'bg-transparent text-secondary-600 hover:bg-secondary-100 hover:text-secondary-900',
    'focus-visible:ring-secondary-400',
  ].join(' '),
  outline: [
    'border border-secondary-300 bg-white text-secondary-700 hover:bg-secondary-50 active:bg-secondary-100',
    'focus-visible:ring-primary-500',
  ].join(' '),
};

const sizeStyles = {
  sm: 'h-8 px-3 text-sm gap-1.5 rounded-lg',
  md: 'h-10 px-4 text-sm gap-2 rounded-lg',
  lg: 'h-12 px-6 text-base gap-2.5 rounded-xl',
};

// ─── Props ───
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variantStyles;
  size?: keyof typeof sizeStyles;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

// ─── Component ───
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      loading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        className={cn(
          // Base styles
          'inline-flex items-center justify-center font-medium transition-all duration-150',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          variantStyles[variant],
          sizeStyles[size],
          fullWidth && 'w-full',
          className
        )}
        disabled={isDisabled}
        {...props}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          leftIcon && <span className="shrink-0">{leftIcon}</span>
        )}
        {children}
        {!loading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
