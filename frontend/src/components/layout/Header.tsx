'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Search, Bell, ChevronDown, LogOut, User, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { logout, getToken } from '@/lib/auth';
import Link from 'next/link';

// ─── Header Props ───
interface HeaderProps {
  title?: string;
  onMenuToggle?: () => void;
}

// ─── Component ───
export function Header({ title, onMenuToggle }: HeaderProps) {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const userMenuRef = useRef<HTMLDivElement>(null);
  const [userEmail, setUserEmail] = useState<string>('');

  // Try to get user email from stored data
  useEffect(() => {
    try {
      const token = getToken();
      if (token) {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const payload = JSON.parse(atob(base64));
        setUserEmail(payload.sub || payload.email || '');
      }
    } catch {
      // ignore
    }
  }, []);

  // Close user menu on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // Navigate to leads with search query
    if (searchValue.trim()) {
      window.location.href = `/leads?search=${encodeURIComponent(searchValue.trim())}`;
    }
  };

  return (
    <header
      className={cn(
        'sticky top-0 z-30 w-full',
        'glass-effect',
        'border-b border-slate-200/60'
      )}
    >
      <div className="flex items-center justify-between h-16 px-4 sm:px-6">
        {/* ─── Left: Mobile menu + Title ─── */}
        <div className="flex items-center gap-3">
          {/* Mobile hamburger */}
          <button
            onClick={onMenuToggle}
            className={cn(
              'p-2 -ml-2 rounded-lg text-slate-500 hover:text-slate-700',
              'hover:bg-slate-100 transition-colors lg:hidden'
            )}
            aria-label="Toggle menu"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {title && (
            <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
          )}
        </div>

        {/* ─── Center: Search ─── */}
        <form
          onSubmit={handleSearch}
          className="hidden md:flex items-center flex-1 max-w-md mx-8"
        >
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search leads..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              className={cn(
                'w-full h-9 pl-9 pr-4 rounded-lg',
                'bg-slate-100 border-0 text-sm text-slate-700',
                'placeholder:text-slate-400',
                'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:bg-white',
                'transition-all duration-200'
              )}
            />
          </div>
        </form>

        {/* ─── Right: Actions ─── */}
        <div className="flex items-center gap-2">
          {/* Mobile search button */}
          <Link
            href="/leads"
            className="p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors md:hidden"
            aria-label="Search"
          >
            <Search className="h-5 w-5" />
          </Link>

          {/* Notifications */}
          <button
            className="relative p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            aria-label="Notifications"
          >
            <Bell className="h-5 w-5" />
            {/* Notification badge */}
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-red-500 ring-2 ring-white" />
          </button>

          {/* ─── User Menu ─── */}
          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className={cn(
                'flex items-center gap-2 pl-2 pr-1 py-1 rounded-lg',
                'hover:bg-slate-100 transition-colors'
              )}
            >
              {/* Avatar */}
              <div className="h-8 w-8 rounded-full bg-primary-600 flex items-center justify-center text-white text-xs font-semibold">
                {userEmail ? userEmail.charAt(0).toUpperCase() : 'U'}
              </div>
              <ChevronDown className="h-4 w-4 text-slate-400 hidden sm:block" />
            </button>

            {/* Dropdown */}
            {userMenuOpen && (
              <div
                className={cn(
                  'absolute right-0 mt-2 w-56',
                  'bg-white rounded-xl border border-slate-200 shadow-lg',
                  'py-1.5 animate-scale-in origin-top-right'
                )}
              >
                {/* User info */}
                <div className="px-4 py-3 border-b border-slate-100">
                  <p className="text-sm font-medium text-slate-900 truncate">
                    {userEmail || 'User'}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5 truncate">{userEmail}</p>
                </div>

                {/* Menu items */}
                <div className="py-1">
                  <Link
                    href="/settings"
                    className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    <User className="h-4 w-4 text-slate-400" />
                    Profile
                  </Link>
                  <Link
                    href="/settings"
                    className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    <Settings className="h-4 w-4 text-slate-400" />
                    Settings
                  </Link>
                </div>

                {/* Logout */}
                <div className="border-t border-slate-100 pt-1">
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      logout();
                    }}
                    className={cn(
                      'flex items-center gap-2.5 w-full px-4 py-2 text-sm',
                      'text-red-600 hover:bg-red-50 transition-colors'
                    )}
                  >
                    <LogOut className="h-4 w-4" />
                    Sign out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
