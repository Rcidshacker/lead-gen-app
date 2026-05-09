import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, parseISO } from 'date-fns';

// ─── Class Name Merger ───
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

// ─── Date Formatting ───
export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? parseISO(date) : date;
  return format(d, 'MMM dd, yyyy');
}

export function formatDateTime(date: string | Date): string {
  const d = typeof date === 'string' ? parseISO(date) : date;
  return format(d, 'MMM dd, yyyy h:mm a');
}

export function formatRelativeTime(date: string | Date): string {
  const d = typeof date === 'string' ? parseISO(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(d);
}

// ─── Currency Formatting ───
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

// ─── String Utilities ───
export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length).trimEnd() + '...';
}

export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function slugify(str: string): string {
  return str
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_]+/g, '-')
    .replace(/--+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// ─── Score Color ───
export function getScoreColor(score: number): {
  text: string;
  bg: string;
  border: string;
} {
  if (score >= 90) {
    return {
      text: 'text-emerald-700',
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
    };
  }
  if (score >= 75) {
    return {
      text: 'text-green-700',
      bg: 'bg-green-50',
      border: 'border-green-200',
    };
  }
  if (score >= 60) {
    return {
      text: 'text-yellow-700',
      bg: 'bg-yellow-50',
      border: 'border-yellow-200',
    };
  }
  if (score >= 30) {
    return {
      text: 'text-orange-700',
      bg: 'bg-orange-50',
      border: 'border-orange-200',
    };
  }
  return {
    text: 'text-red-700',
    bg: 'bg-red-50',
    border: 'border-red-200',
  };
}

export function getScoreLabel(score: number): string {
  if (score >= 90) return 'Excellent';
  if (score >= 75) return 'Good';
  if (score >= 60) return 'Fair';
  if (score >= 30) return 'Low';
  return 'Poor';
}

// ─── Platform Icon Helper ───
export function getPlatformIcon(platform: string): string {
  const icons: Record<string, string> = {
    linkedin: 'Linkedin',
    indeed: 'Briefcase',
    upwork: 'Laptop',
    naukri: 'Globe',
    glassdoor: 'DoorOpen',
    ziprecruiter: 'Zap',
    monster: 'Flame',
    angelist: 'Angel',
    wellfound: 'Rocket',
    default: 'Globe',
  };
  return icons[platform.toLowerCase()] || icons.default;
}

// ─── Number Formatting ───
export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

export function formatCompactNumber(num: number): string {
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    compactDisplay: 'short',
  }).format(num);
}

// ─── Status Helpers ───
export function getStatusColor(status: string): {
  text: string;
  bg: string;
  dot: string;
} {
  const colors: Record<string, { text: string; bg: string; dot: string }> = {
    new: { text: 'text-blue-700', bg: 'bg-blue-50', dot: 'bg-blue-500' },
    contacted: { text: 'text-amber-700', bg: 'bg-amber-50', dot: 'bg-amber-500' },
    interested: { text: 'text-emerald-700', bg: 'bg-emerald-50', dot: 'bg-emerald-500' },
    rejected: { text: 'text-red-700', bg: 'bg-red-50', dot: 'bg-red-500' },
    hired: { text: 'text-violet-700', bg: 'bg-violet-50', dot: 'bg-violet-500' },
  };
  return colors[status] || colors.new;
}
