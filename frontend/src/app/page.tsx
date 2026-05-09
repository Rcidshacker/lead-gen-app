'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/auth';

// ─── Root Redirect Page ───
// Redirects to /dashboard if authenticated, /login if not.
export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    const authed = isAuthenticated();
    router.replace(authed ? '/dashboard' : '/login');
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-lg bg-primary-600 animate-pulse" />
        <span className="text-slate-400 text-sm">Loading...</span>
      </div>
    </div>
  );
}
