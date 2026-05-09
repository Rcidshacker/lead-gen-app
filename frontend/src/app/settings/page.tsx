'use client';

import React, { useState } from 'react';
import {
  User,
  Key,
  Settings2,
  Bell,
  Save,
  Eye,
  EyeOff,
  Copy,
  Check,
} from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardBody } from '@/components/ui/Card';
import { cn } from '@/lib/utils';

// ─── Tab Config ───
const tabs = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'api-keys', label: 'API Keys', icon: Key },
  { id: 'scraping', label: 'Scraping Preferences', icon: Settings2 },
  { id: 'notifications', label: 'Notifications', icon: Bell },
] as const;

type TabId = (typeof tabs)[number]['id'];

// ─── Settings Page ───
export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('profile');

  // ── Profile state ──
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');

  // ── API Keys state ──
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [showOpenai, setShowOpenai] = useState(false);
  const [showAnthropic, setShowAnthropic] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // ── Scraping state ──
  const [defaultDelay, setDefaultDelay] = useState('2');
  const [maxConcurrent, setMaxConcurrent] = useState('3');
  const [timeout, setTimeout_] = useState('30');

  // ── Notifications state ──
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [webhookUrl, setWebhookUrl] = useState('');

  const handleCopy = async (value: string, field: string) => {
    await navigator.clipboard.writeText(value);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleSave = () => {
    // In production, this would call an API to persist settings
    alert('Settings saved! (This is a demo)');
  };

  return (
    <AppShell title="Settings">
      <p className="text-sm text-slate-500 mb-6">
        Manage your account settings and preferences.
      </p>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* ─── Tab Navigation ─── */}
        <nav className="lg:w-60 shrink-0">
          <div className="flex lg:flex-col gap-1 overflow-x-auto lg:overflow-visible">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
                    active
                      ? 'text-primary-600 bg-primary-50'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  )}
                >
                  <Icon className={cn('h-4 w-4', active && 'text-primary-600')} />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </nav>

        {/* ─── Tab Content ─── */}
        <div className="flex-1 max-w-2xl">
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <Card padding="lg">
              <CardHeader>
                <CardTitle>Profile</CardTitle>
              </CardHeader>
              <CardBody className="space-y-5">
                <Input
                  label="Full Name"
                  placeholder="John Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  leftIcon={<User className="h-4 w-4" />}
                />
                <Input
                  label="Email"
                  type="email"
                  placeholder="john@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  helperText="Your email is used for notifications and account recovery."
                />
                <div className="pt-3">
                  <Button leftIcon={<Save className="h-4 w-4" />} onClick={handleSave}>
                    Save Profile
                  </Button>
                </div>
              </CardBody>
            </Card>
          )}

          {/* API Keys Tab */}
          {activeTab === 'api-keys' && (
            <Card padding="lg">
              <CardHeader>
                <CardTitle>API Keys</CardTitle>
              </CardHeader>
              <CardBody className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    OpenAI API Key
                  </label>
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <input
                        type={showOpenai ? 'text' : 'password'}
                        value={openaiKey}
                        onChange={(e) => setOpenaiKey(e.target.value)}
                        placeholder="sk-..."
                        className={cn(
                          'w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 pr-10',
                          'text-sm text-slate-900 placeholder:text-slate-400',
                          'focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500',
                          'transition-colors duration-150'
                        )}
                      />
                      <button
                        type="button"
                        onClick={() => setShowOpenai(!showOpenai)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        {showOpenai ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCopy(openaiKey, 'openai')}
                      leftIcon={
                        copiedField === 'openai' ? (
                          <Check className="h-3.5 w-3.5" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )
                      }
                    >
                      {copiedField === 'openai' ? 'Copied' : 'Copy'}
                    </Button>
                  </div>
                  <p className="mt-1.5 text-xs text-slate-500">
                    Used for AI-powered lead scoring and analysis.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Anthropic API Key
                  </label>
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <input
                        type={showAnthropic ? 'text' : 'password'}
                        value={anthropicKey}
                        onChange={(e) => setAnthropicKey(e.target.value)}
                        placeholder="sk-ant-..."
                        className={cn(
                          'w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 pr-10',
                          'text-sm text-slate-900 placeholder:text-slate-400',
                          'focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500',
                          'transition-colors duration-150'
                        )}
                      />
                      <button
                        type="button"
                        onClick={() => setShowAnthropic(!showAnthropic)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        {showAnthropic ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCopy(anthropicKey, 'anthropic')}
                      leftIcon={
                        copiedField === 'anthropic' ? (
                          <Check className="h-3.5 w-3.5" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )
                      }
                    >
                      {copiedField === 'anthropic' ? 'Copied' : 'Copy'}
                    </Button>
                  </div>
                  <p className="mt-1.5 text-xs text-slate-500">
                    Used as an alternative AI provider for lead analysis.
                  </p>
                </div>

                <div className="pt-3">
                  <Button leftIcon={<Save className="h-4 w-4" />} onClick={handleSave}>
                    Save API Keys
                  </Button>
                </div>
              </CardBody>
            </Card>
          )}

          {/* Scraping Preferences Tab */}
          {activeTab === 'scraping' && (
            <Card padding="lg">
              <CardHeader>
                <CardTitle>Scraping Preferences</CardTitle>
              </CardHeader>
              <CardBody className="space-y-5">
                <Input
                  label="Default Delay (seconds)"
                  type="number"
                  value={defaultDelay}
                  onChange={(e) => setDefaultDelay(e.target.value)}
                  helperText="Time to wait between page requests to avoid rate limiting."
                  min={0}
                  max={60}
                />
                <Input
                  label="Max Concurrent Scrapes"
                  type="number"
                  value={maxConcurrent}
                  onChange={(e) => setMaxConcurrent(e.target.value)}
                  helperText="Maximum number of scraping jobs that can run simultaneously."
                  min={1}
                  max={10}
                />
                <Input
                  label="Request Timeout (seconds)"
                  type="number"
                  value={timeout}
                  onChange={(e) => setTimeout_(e.target.value)}
                  helperText="Maximum time to wait for a page to load before timing out."
                  min={5}
                  max={120}
                />
                <div className="pt-3">
                  <Button leftIcon={<Save className="h-4 w-4" />} onClick={handleSave}>
                    Save Preferences
                  </Button>
                </div>
              </CardBody>
            </Card>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <Card padding="lg">
              <CardHeader>
                <CardTitle>Notifications</CardTitle>
              </CardHeader>
              <CardBody className="space-y-5">
                {/* Email Toggle */}
                <div className="flex items-center justify-between py-2">
                  <div>
                    <p className="text-sm font-medium text-slate-900">Email Notifications</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Receive email alerts when new leads are found or scraping jobs fail.
                    </p>
                  </div>
                  <button
                    onClick={() => setEmailNotifications(!emailNotifications)}
                    className={cn(
                      'relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors duration-200',
                      emailNotifications ? 'bg-primary-600' : 'bg-slate-200'
                    )}
                    role="switch"
                    aria-checked={emailNotifications}
                  >
                    <span
                      className={cn(
                        'inline-block h-5 w-5 rounded-full bg-white shadow-sm transform transition-transform duration-200 mt-0.5',
                        emailNotifications ? 'translate-x-[22px]' : 'translate-x-0.5'
                      )}
                    />
                  </button>
                </div>

                {/* Webhook URL */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Webhook URL
                  </label>
                  <input
                    type="url"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    placeholder="https://your-app.com/api/webhook"
                    className={cn(
                      'w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5',
                      'text-sm text-slate-900 placeholder:text-slate-400',
                      'focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500',
                      'transition-colors duration-150'
                    )}
                  />
                  <p className="mt-1.5 text-xs text-slate-500">
                    Receive webhook notifications when events occur. The payload will be sent as a POST request.
                  </p>
                </div>

                <div className="pt-3">
                  <Button leftIcon={<Save className="h-4 w-4" />} onClick={handleSave}>
                    Save Notifications
                  </Button>
                </div>
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </AppShell>
  );
}
