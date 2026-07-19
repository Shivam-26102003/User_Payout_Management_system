'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Wallet, Shield, Users, ArrowRight, CheckCircle2, Lock, ArrowLeft } from 'lucide-react';
import { api } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  
  // Navigation & Toggle States
  const [isSignup, setIsSignup] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form Fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [signupRole, setSignupRole] = useState<'USER' | 'ADMIN'>('USER');

  // Clear previous session on load
  useEffect(() => {
    localStorage.removeItem('payout_access_token');
    localStorage.removeItem('user_role');
  }, []);

  const handleLogin = async (e: React.FormEvent, customCreds?: { email: string; pass: string }) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    const targetEmail = customCreds ? customCreds.email : email;
    const targetPass = customCreds ? customCreds.pass : password;

    if (!targetEmail || !targetPass) {
      setError('Please fill in all credentials.');
      setLoading(false);
      return;
    }

    try {
      const form = new FormData();
      form.append('username', targetEmail);
      form.append('password', targetPass);

      const res = await api.login(form);
      
      localStorage.setItem('payout_access_token', res.access_token);
      localStorage.setItem('user_role', res.role);

      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    if (!email || !password || !name) {
      setError('Please fill in all fields.');
      setLoading(false);
      return;
    }

    try {
      // 1. Create the user
      await api.signup({
        email,
        name,
        password,
        role: signupRole,
        status: 'ACTIVE'
      });

      setSuccess('Account created successfully! Logging you in...');
      
      // 2. Perform auto-login
      setTimeout(async () => {
        try {
          const form = new FormData();
          form.append('username', email);
          form.append('password', password);

          const res = await api.login(form);
          localStorage.setItem('payout_access_token', res.access_token);
          localStorage.setItem('user_role', res.role);
          router.push('/dashboard');
        } catch (loginErr: any) {
          setError('Account created, but automatic sign in failed. Please sign in manually.');
          setIsSignup(false);
          setLoading(false);
        }
      }, 1500);

    } catch (err: any) {
      setError(err.message || 'Registration failed. Email might already be taken.');
      setLoading(false);
    }
  };

  const seedLogins = [
    {
      role: 'Platform Administrator',
      email: 'admin@example.com',
      pass: 'adminpassword',
      icon: Shield,
      color: 'from-purple-500 to-indigo-500',
    },
    {
      role: 'Affiliate Marketing User',
      email: 'affiliate@example.com',
      pass: 'userpassword',
      icon: Users,
      color: 'from-emerald-500 to-teal-500',
    },
    {
      role: 'Guest Auditor (Viewer)',
      email: 'viewer@example.com',
      pass: 'viewerpassword',
      icon: Wallet,
      color: 'from-amber-500 to-orange-500',
    },
  ];

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#09090b] text-white">
      {/* Visual Section */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-[#121214] via-[#0d0d0f] to-[#09090b] border-r border-[#1f1f23] relative overflow-hidden">
        {/* Glow Effects */}
        <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-96 h-96 bg-teal-600/10 rounded-full blur-3xl" />

        <div className="flex items-center gap-3 relative z-10">
          <div className="w-10 h-10 rounded-xl bg-purple-600 flex items-center justify-center shadow-lg shadow-purple-600/20">
            <Wallet className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-zinc-400">
            Payout Ledger
          </span>
        </div>

        <div className="relative z-10 max-w-md my-auto space-y-6">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl font-extrabold tracking-tight leading-none"
          >
            Double-Entry <br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-teal-300">
              Financial Payout
            </span> <br />
            Infrastructure.
          </motion.h1>
          <p className="text-zinc-400 text-sm leading-relaxed">
            A production-ready payout management engine supporting 10% advance payments on pending sales, automated reconciliation balance adjustments, and failed transaction recoveries.
          </p>
          <div className="space-y-3 pt-4">
            <div className="flex items-center gap-3 text-xs text-zinc-400">
              <CheckCircle2 className="w-4 h-4 text-purple-400" />
              <span>Decimal-precision Value Objects</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-zinc-400">
              <CheckCircle2 className="w-4 h-4 text-purple-400" />
              <span>Balanced Double-Entry accounting ledgers</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-zinc-400">
              <CheckCircle2 className="w-4 h-4 text-purple-400" />
              <span>Idempotent execution guarantees</span>
            </div>
          </div>
        </div>

        <div className="text-zinc-500 text-xs relative z-10">
          © 2026 Payout System. All rights reserved.
        </div>
      </div>

      {/* Forms Section */}
      <div className="flex flex-col justify-center px-6 py-12 md:px-12 xl:px-24 relative overflow-hidden">
        <div className="max-w-md w-full mx-auto space-y-8 relative z-10">
          <AnimatePresence mode="wait">
            {!isSignup ? (
              /* --- SIGN IN VIEW --- */
              <motion.div
                key="signin"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
              >
                <div className="space-y-2">
                  <h2 className="text-2xl font-bold tracking-tight">Access Dashboard</h2>
                  <p className="text-sm text-zinc-400">
                    Sign in to manage your affiliate revenues or reconcile sales ledger records.
                  </p>
                </div>

                {error && (
                  <div className="p-3.5 bg-red-950/40 border border-red-900/50 text-red-300 text-xs rounded-lg flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-red-400 animate-ping" />
                    <span>{error}</span>
                  </div>
                )}

                <form className="space-y-4" onSubmit={(e) => handleLogin(e)}>
                  <div className="space-y-1.5">
                    <label className="text-xs text-zinc-400 font-medium">Email Address</label>
                    <input
                      type="email"
                      required
                      className="w-full bg-[#121214] border border-[#1f1f23] rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition-colors"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-zinc-400 font-medium">Password</label>
                    <input
                      type="password"
                      required
                      className="w-full bg-[#121214] border border-[#1f1f23] rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition-colors"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-900 text-sm font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors cursor-pointer group shadow-lg shadow-purple-600/10"
                  >
                    {loading ? 'Authenticating...' : 'Sign In'}
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                  </button>
                </form>

                <div className="text-center">
                  <span className="text-xs text-zinc-400">First time using the platform? </span>
                  <button 
                    onClick={() => { setError(''); setSuccess(''); setIsSignup(true); }}
                    className="text-xs text-purple-400 hover:text-purple-300 font-semibold cursor-pointer underline"
                  >
                    Create an account
                  </button>
                </div>

                {/* Quick switcher */}
                <div className="relative pt-4">
                  <div className="absolute inset-0 flex items-center" aria-hidden="true">
                    <div className="w-full border-t border-[#1f1f23]" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-[#09090b] px-2 text-zinc-500 font-medium">Quick Credentials Switcher</span>
                  </div>
                </div>

                <div className="grid gap-2.5">
                  {seedLogins.map((login) => {
                    const Icon = login.icon;
                    return (
                      <button
                        key={login.role}
                        onClick={() => handleLogin(null as any, { email: login.email, pass: login.pass })}
                        disabled={loading}
                        className="flex items-center justify-between p-3 bg-[#121214] hover:bg-[#161619] border border-[#1f1f23] hover:border-zinc-700/60 rounded-xl transition-all text-left cursor-pointer group"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${login.color} flex items-center justify-center`}>
                            <Icon className="w-4 h-4 text-white" />
                          </div>
                          <div>
                            <div className="text-xs font-semibold text-zinc-200">{login.role}</div>
                            <div className="text-[10px] text-zinc-500">{login.email}</div>
                          </div>
                        </div>
                        <div className="w-6 h-6 rounded-full bg-zinc-900/80 flex items-center justify-center group-hover:bg-zinc-800 transition-colors">
                          <Lock className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300" />
                        </div>
                      </button>
                    );
                  })}
                </div>
              </motion.div>
            ) : (
              /* --- SIGN UP VIEW --- */
              <motion.div
                key="signup"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
              >
                <div className="space-y-2">
                  <button 
                    onClick={() => { setError(''); setSuccess(''); setIsSignup(false); }}
                    className="flex items-center gap-1.5 text-zinc-400 hover:text-white text-xs font-semibold transition-colors cursor-pointer mb-2"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    Back to Sign In
                  </button>
                  <h2 className="text-2xl font-bold tracking-tight">Create Account</h2>
                  <p className="text-sm text-zinc-400">
                    Register a new user account on the Secure Payout platform.
                  </p>
                </div>

                {error && (
                  <div className="p-3.5 bg-red-950/40 border border-red-900/50 text-red-300 text-xs rounded-lg flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
                    <span>{error}</span>
                  </div>
                )}

                {success && (
                  <div className="p-3.5 bg-emerald-950/40 border border-emerald-900/50 text-emerald-300 text-xs rounded-lg flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                    <span>{success}</span>
                  </div>
                )}

                <form className="space-y-4" onSubmit={handleSignup}>
                  <div className="space-y-1.5">
                    <label className="text-xs text-zinc-400 font-medium">Full Name</label>
                    <input
                      type="text"
                      required
                      className="w-full bg-[#121214] border border-[#1f1f23] rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition-colors"
                      placeholder="Jane Doe"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  </div>
                  
                  <div className="space-y-1.5">
                    <label className="text-xs text-zinc-400 font-medium">Email Address</label>
                    <input
                      type="email"
                      required
                      className="w-full bg-[#121214] border border-[#1f1f23] rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition-colors"
                      placeholder="jane@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs text-zinc-400 font-medium">Password</label>
                    <input
                      type="password"
                      required
                      className="w-full bg-[#121214] border border-[#1f1f23] rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition-colors"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs text-zinc-400 font-medium">Assigned Platform Role</label>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        type="button"
                        onClick={() => setSignupRole('USER')}
                        className={`py-2 px-3 text-xs font-semibold rounded-lg border text-center transition-all cursor-pointer ${
                          signupRole === 'USER'
                            ? 'bg-purple-600/10 border-purple-500 text-purple-400'
                            : 'bg-zinc-900 border-[#1f1f23] text-zinc-400 hover:text-white'
                        }`}
                      >
                        Affiliate User
                      </button>
                      <button
                        type="button"
                        onClick={() => setSignupRole('ADMIN')}
                        className={`py-2 px-3 text-xs font-semibold rounded-lg border text-center transition-all cursor-pointer ${
                          signupRole === 'ADMIN'
                            ? 'bg-purple-600/10 border-purple-500 text-purple-400'
                            : 'bg-zinc-900 border-[#1f1f23] text-zinc-400 hover:text-white'
                        }`}
                      >
                        Administrator
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-900 text-sm font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors cursor-pointer group shadow-lg shadow-purple-600/10"
                  >
                    {loading ? 'Creating Account...' : 'Complete Sign Up'}
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                  </button>
                </form>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
