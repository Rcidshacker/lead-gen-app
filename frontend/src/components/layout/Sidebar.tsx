'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Zap,
  LayoutDashboard,
  Globe,
  Users,
  Clock,
  Settings,
  X,
  ChevronLeft,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Navigation Items ───
interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/sources', label: 'Sources', icon: Globe },
  { href: '/leads', label: 'Leads', icon: Users },
  { href: '/jobs', label: 'Jobs', icon: Clock },
  { href: '/settings', label: 'Settings', icon: Settings },
];

// ─── Sidebar Props ───
interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

// ─── Component ───
export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard' || pathname === '/';
    return pathname.startsWith(href);
  };

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* ─── Logo / Brand ─── */}
      <div className="flex items-center justify-between h-16 px-6 shrink-0">
        <Link href="/dashboard" className="flex items-center gap-2.5 group">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary-600 shadow-md shadow-primary-600/25 group-hover:shadow-primary-600/40 transition-shadow">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-bold text-white tracking-tight">
            LeadForge
          </span>
        </Link>

        {/* Mobile close button */}
        <button
          onClick={onClose}
          className={cn(
            'p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10',
            'transition-colors lg:hidden'
          )}
          aria-label="Close sidebar"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* ─── Navigation ─── */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <p className="px-3 mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          Menu
        </p>
        {navItems.map((item) => {
          const active = isActive(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium',
                'transition-all duration-150',
                active
                  ? 'text-white bg-primary-600/20 border-l-2 border-primary-400 pl-[10px]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
              )}
            >
              <Icon className={cn('h-5 w-5 shrink-0', active && 'text-primary-400')} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* ─── Footer ─── */}
      <div className="px-3 py-4 border-t border-white/10 shrink-0">
        <div className="px-3 py-3 rounded-lg bg-white/5">
          <p className="text-xs font-medium text-slate-300">LeadForge v0.1.0</p>
          <p className="mt-0.5 text-xs text-slate-500">
            AI-Powered Lead Generation
          </p>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* ─── Desktop Sidebar ─── */}
      <aside
        className={cn(
          'hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 lg:z-40',
          'w-64 bg-slate-900 border-r border-white/10'
        )}
      >
        {sidebarContent}
      </aside>

      {/* ─── Mobile Overlay ─── */}
      {isOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 animate-fade-in"
            onClick={onClose}
            aria-hidden="true"
          />
          {/* Sidebar Panel */}
          <aside
            className={cn(
              'fixed inset-y-0 left-0 z-50 w-64 bg-slate-900',
              'animate-slide-in shadow-2xl'
            )}
          >
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
}

export default Sidebar;
