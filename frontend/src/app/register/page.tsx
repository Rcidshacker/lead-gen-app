'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Zap, Mail, Lock, User, Eye, EyeOff } from 'lucide-react';
import { register, login } from '@/lib/auth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardBody } from '@/components/ui/Card';

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!fullName.trim()) { setError('Full name is required'); return; }
    if (!email.trim())    { setError('Email is required'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return; }

    setLoading(true);
    try {
      await register(email, password, fullName);
      // Auto-login after successful registration
      await login(email, password);
      router.push('/dashboard');
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Registration failed. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md">
        {/* Branding */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2.5">
            <div className="flex items-center justify-center w-11 h-11 rounded-xl bg-primary-600 shadow-lg shadow-primary-600/25">
              <Zap className="h-6 w-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-slate-900 tracking-tight">
              LeadForge
            </span>
          </Link>
          <p className="mt-3 text-sm text-slate-500">
            AI-Powered Lead Generation Platform
          </p>
        </div>

        {/* Register Card */}
        <Card padding="lg">
          <CardBody>
            <div className="mb-6">
              <h1 className="text-xl font-semibold text-slate-900">Create your account</h1>
              <p className="text-sm text-slate-500 mt-1">
                Get started with LeadForge for free
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <Input
                label="Full name"
                type="text"
                placeholder="Your name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                leftIcon={<User className="h-4 w-4" />}
                autoComplete="name"
                required
              />

              <Input
                label="Email address"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                leftIcon={<Mail className="h-4 w-4" />}
                autoComplete="email"
                required
              />

              <Input
                label="Password"
                type={showPassword ? 'text' : 'password'}
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                leftIcon={<Lock className="h-4 w-4" />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="hover:text-slate-600 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
                autoComplete="new-password"
                required
              />

              <Button type="submit" loading={loading} fullWidth size="lg">
                Create Account
              </Button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm text-slate-500">
                Already have an account?{' '}
                <Link
                  href="/login"
                  className="font-medium text-primary-600 hover:text-primary-700 transition-colors"
                >
                  Sign in
                </Link>
              </p>
            </div>
          </CardBody>
        </Card>

        <p className="mt-6 text-center text-xs text-slate-400">
          &copy; {new Date().getFullYear()} LeadForge. All rights reserved.
        </p>
      </div>
    </div>
  );
}
