import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Providers } from './providers';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: {
    default: 'LeadForge — AI-Powered Lead Generation',
    template: '%s | LeadForge',
  },
  description:
    'Automate lead generation across multiple job platforms with AI-powered scoring, contact extraction, and intelligent filtering.',
  keywords: ['lead generation', 'job scraping', 'AI', 'automation', 'recruitment'],
  authors: [{ name: 'LeadForge' }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className={`${inter.className} min-h-screen bg-slate-50`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
