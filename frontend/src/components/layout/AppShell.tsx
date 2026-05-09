'use client';

import React, { useState, type ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

// ─── Props ───
interface AppShellProps {
  children: ReactNode;
  title?: string;
}

// ─── Component ───
export function AppShell({ children, title }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="lg:pl-64">
        {/* Header */}
        <Header
          title={title}
          onMenuToggle={() => setSidebarOpen(true)}
        />

        {/* Page Content */}
        <main className="p-4 sm:p-6 lg:p-8">
          <div className="animate-fade-in">{children}</div>
        </main>
      </div>
    </div>
  );
}

export default AppShell;
