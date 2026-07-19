'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Wallet, Shield, Users, RefreshCw, LogOut, CheckCircle, XCircle, 
  Clock, ArrowUpRight, ArrowDownLeft, AlertCircle, FileText, Download, 
  Search, SlidersHorizontal, CheckSquare, Square, Bell, Layers, ChevronRight, Activity
} from 'lucide-react';
import { api, Sale, Withdrawal, LedgerTransaction, AuditLog, DashboardStats, User } from '@/lib/api';

export default function Dashboard() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [role, setRole] = useState<'ADMIN' | 'USER' | 'VIEWER'>('USER');
  const [activeTab, setActiveTab] = useState<'overview' | 'sales' | 'withdrawals' | 'ledger' | 'audits' | 'affiliates'>('overview');
  
  // States
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [sales, setSales] = useState<Sale[]>([]);
  const [withdrawals, setWithdrawals] = useState<Withdrawal[]>([]);
  const [ledger, setLedger] = useState<LedgerTransaction[]>([]);
  const [audits, setAudits] = useState<AuditLog[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [profile, setProfile] = useState<User | null>(null);
  const [affiliates, setAffiliates] = useState<any[]>([]);
  const [selectedAffiliate, setSelectedAffiliate] = useState<any | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');
  
  // Loading & Actions
  const [loading, setLoading] = useState(true);
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [withdrawLoading, setWithdrawLoading] = useState(false);
  const [jobLoading, setJobLoading] = useState(false);
  const [reconcileSelected, setReconcileSelected] = useState<Record<string, 'APPROVED' | 'REJECTED'>>({});
  
  // Ingest Sale Form
  const [ingestUserId, setIngestUserId] = useState('');
  const [ingestBrand, setIngestBrand] = useState('Nike');
  const [ingestAmount, setIngestAmount] = useState('');
  const [ingestLoading, setIngestLoading] = useState(false);
  
  // Feedback
  const [toasts, setToasts] = useState<{ id: number; message: string; type: 'success' | 'error' | 'info' }[]>([]);
  const toastIdRef = useRef(0);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = toastIdRef.current++;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  const handleLogout = () => {
    localStorage.removeItem('payout_access_token');
    localStorage.removeItem('user_role');
    router.push('/');
  };

  // Fetch initial configs
  useEffect(() => {
    setMounted(true);
    const token = localStorage.getItem('payout_access_token');
    const storedRole = localStorage.getItem('user_role') as any;
    if (!token) {
      router.push('/');
      return;
    }
    if (storedRole) {
      setRole(storedRole);
    }
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      // Current profile
      const userProfile = await api.request<User>("/users/me").catch(() => null);
      let currentRole = role;
      if (userProfile) {
        setProfile(userProfile);
        setRole(userProfile.role);
        currentRole = userProfile.role;
      }

      const isAdmin = currentRole === 'ADMIN';
      let targetUserId = selectedAffiliate ? selectedAffiliate.id : undefined;
      let initialSelectedAff = selectedAffiliate;

      if (isAdmin) {
        const [auditData, usersData, affiliatesData] = await Promise.all([
          api.getAuditLogs().catch(() => ({ logs: [], total: 0 })),
          api.getUsers().catch(() => []),
          api.getAffiliates(searchQuery, sortBy, sortOrder).catch(() => []),
        ]);
        setAudits(auditData.logs);
        setUsers(usersData);
        setAffiliates(affiliatesData);

        const affiliateUsers = usersData.filter((u: any) => u.role === 'USER');
        
        // Default to first affiliate on startup if none selected
        if (affiliateUsers.length > 0 && !selectedAffiliate) {
          const firstAff = affiliatesData.find(a => a.id === affiliateUsers[0].id) || affiliateUsers[0];
          setSelectedAffiliate(firstAff);
          initialSelectedAff = firstAff;
          targetUserId = firstAff.id;
        }

        if (affiliateUsers.length > 0 && !ingestUserId) {
          setIngestUserId(initialSelectedAff ? initialSelectedAff.id : affiliateUsers[0].id);
        }
      }

      const [statsData, salesData, withdrawalsData, ledgerData] = await Promise.all([
        api.getDashboardStats(targetUserId).catch(() => null),
        api.getSales(undefined, targetUserId).catch(() => []),
        api.getWithdrawals(targetUserId).catch(() => []),
        api.getLedger(targetUserId).catch(() => []),
      ]);

      if (statsData) setStats(statsData);
      setSales(salesData);
      setWithdrawals(withdrawalsData);
      setLedger(ledgerData);
    } catch (err: any) {
      showToast(err.message || "Failed to load data", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (storedRoleIsAdmin() && activeTab === 'affiliates') {
      const delayDebounceFn = setTimeout(() => {
        api.getAffiliates(searchQuery, sortBy, sortOrder)
          .then(res => setAffiliates(res))
          .catch(err => showToast(err.message || "Failed to load affiliates", "error"));
      }, 300);

      return () => clearTimeout(delayDebounceFn);
    }
  }, [searchQuery, sortBy, sortOrder, activeTab]);

  const selectAffiliateAndLoad = async (affiliate: any) => {
    setSelectedAffiliate(affiliate);
    if (affiliate) {
      setIngestUserId(affiliate.id);
    }
    setLoading(true);
    try {
      const targetUserId = affiliate ? affiliate.id : undefined;
      const [statsData, salesData, withdrawalsData, ledgerData] = await Promise.all([
        api.getDashboardStats(targetUserId).catch(() => null),
        api.getSales(undefined, targetUserId).catch(() => []),
        api.getWithdrawals(targetUserId).catch(() => []),
        api.getLedger(targetUserId).catch(() => []),
      ]);

      if (statsData) setStats(statsData);
      setSales(salesData);
      setWithdrawals(withdrawalsData);
      setLedger(ledgerData);
      if (affiliate) {
        showToast(`Now viewing ${affiliate.name}'s space`, "info");
      } else {
        showToast("Now viewing all affiliates space", "info");
      }
    } catch (err: any) {
      showToast(err.message || "Failed to load affiliate details", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAffiliate = async (affiliate: any) => {
    setSelectedAffiliate(affiliate);
    if (affiliate) {
      setIngestUserId(affiliate.id);
    }
    setLoading(true);
    try {
      const [statsData, salesData, withdrawalsData, ledgerData] = await Promise.all([
        api.getDashboardStats(affiliate.id).catch(() => null),
        api.getSales(undefined, affiliate.id).catch(() => []),
        api.getWithdrawals(affiliate.id).catch(() => []),
        api.getLedger(affiliate.id).catch(() => []),
      ]);

      if (statsData) setStats(statsData);
      setSales(salesData);
      setWithdrawals(withdrawalsData);
      setLedger(ledgerData);
      setActiveTab('overview'); // Switch to overview tab for the selected affiliate!
      showToast(`Now inspecting ${affiliate.name}`, "info");
    } catch (err: any) {
      showToast(err.message || "Failed to load affiliate details", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleClearAffiliate = async () => {
    setSelectedAffiliate(null);
    setLoading(true);
    try {
      const [statsData, salesData, withdrawalsData, ledgerData] = await Promise.all([
        api.getDashboardStats().catch(() => null),
        api.getSales().catch(() => []),
        api.getWithdrawals().catch(() => []),
        api.getLedger().catch(() => []),
      ]);

      if (statsData) setStats(statsData);
      setSales(salesData);
      setWithdrawals(withdrawalsData);
      setLedger(ledgerData);
      showToast("Cleared inspect filter", "info");
    } catch (err: any) {
      showToast(err.message || "Failed to clear inspect filter", "error");
    } finally {
      setLoading(false);
    }
  };

  const storedRoleIsAdmin = () => {
    if (!mounted) return false;
    if (typeof window !== "undefined") {
      return localStorage.getItem('user_role') === 'ADMIN';
    }
    return role === 'ADMIN';
  };

  // Trigger Advance Payout Job
  const triggerAdvancePayoutJob = async () => {
    setJobLoading(true);
    try {
      const res = await api.runAdvancePayout();
      showToast(`Advance payout job completed. Processed ${res.processed_count} sales.`, "success");
      await loadAllData();
    } catch (err: any) {
      showToast(err.message || "Failed to run job", "error");
    } finally {
      setJobLoading(false);
    }
  };

  // Submit Bulk Reconciliation
  const executeReconciliation = async () => {
    const list = Object.entries(reconcileSelected).map(([sale_id, action]) => ({
      sale_id,
      action
    }));

    if (list.length === 0) {
      showToast("No sales selected for reconciliation", "info");
      return;
    }

    setJobLoading(true);
    try {
      await api.reconcileSales(list);
      showToast("Reconciliation batch successfully completed.", "success");
      setReconcileSelected({});
      await loadAllData();
    } catch (err: any) {
      showToast(err.message || "Reconciliation failed", "error");
    } finally {
      setJobLoading(false);
    }
  };

  // Ingest Sale
  const handleIngestSale = async (e: React.FormEvent) => {
    e.preventDefault();
    const finalUserId = selectedAffiliate ? selectedAffiliate.id : ingestUserId;
    if (!finalUserId || !ingestAmount) {
      showToast("Please complete the ingestion fields", "error");
      return;
    }

    setIngestLoading(true);
    try {
      const externalId = `sale_ref_${Date.now().toString().slice(-6)}`;
      await api.createSale({
        user_id: finalUserId,
        brand_name: ingestBrand,
        external_id: externalId,
        amount: parseFloat(ingestAmount)
      });
      showToast(`Sale ${externalId} ingested successfully.`, "success");
      setIngestAmount('');
      await loadAllData();
    } catch (err: any) {
      showToast(err.message || "Ingestion failed", "error");
    } finally {
      setIngestLoading(false);
    }
  };

  // Request Withdrawal
  const handleWithdrawalRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    const amountVal = parseFloat(withdrawAmount);
    if (isNaN(amountVal) || amountVal <= 0) {
      showToast("Please enter a valid positive amount", "error");
      return;
    }

    setWithdrawLoading(true);
    try {
      await api.createWithdrawal(amountVal);
      showToast("Withdrawal request created successfully", "success");
      setWithdrawAmount('');
      await loadAllData();
    } catch (err: any) {
      showToast(err.message || "Withdrawal failed", "error");
    } finally {
      setWithdrawLoading(false);
    }
  };

  // Webhook Failure Simulator (Admin only)
  const handleSimulateWebhookResult = async (withdrawalId: string, targetStatus: 'COMPLETED' | 'FAILED') => {
    try {
      await api.updateWithdrawalStatus(
        withdrawalId, 
        targetStatus, 
        targetStatus === 'FAILED' ? 'Mock Payment Gateway rejection: INSUFFICIENT_FUNDS' : undefined
      );
      showToast(`Payout callback processed: Status set to ${targetStatus}`, "success");
      await loadAllData();
    } catch (err: any) {
      showToast(err.message || "Simulation failed", "error");
    }
  };

  // CSV Exporter
  const exportCSV = (data: any[], filename: string) => {
    if (data.length === 0) return;
    const headers = Object.keys(data[0]).join(',');
    const rows = data.map(row => 
      Object.values(row).map(val => `"${String(val).replace(/"/g, '""')}"`).join(',')
    );
    const csvContent = "data:text/csv;charset=utf-8," + [headers, ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${filename}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast(`${filename}.csv exported successfully`, "success");
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-white flex">
      {/* Sidebar navigation */}
      <aside className="w-64 bg-[#121214] border-r border-[#1f1f23] p-6 flex flex-col justify-between flex-shrink-0">
        <div className="space-y-8">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-purple-600 flex items-center justify-center shadow shadow-purple-600/30">
              <Wallet className="w-4.5 h-4.5 text-white" />
            </div>
            <span className="font-bold text-md tracking-tight">Payouts</span>
            <span className="text-[10px] uppercase font-semibold text-zinc-500 bg-zinc-900 border border-zinc-800 px-1.5 py-0.5 rounded">
              v1.0
            </span>
          </div>

          {/* Profile Card */}
          {profile && (
            <div className="p-3 bg-[#161619] rounded-xl border border-[#1f1f23]">
              <div className="text-xs font-semibold text-zinc-300 truncate">{profile.name}</div>
              <div className="text-[10px] text-zinc-500 truncate mb-2">{profile.email}</div>
              <div className="flex items-center justify-between">
                <span className="text-[9px] uppercase font-extrabold text-purple-400 bg-purple-950/40 border border-purple-900/50 px-1.5 py-0.5 rounded">
                  {role}
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              </div>
            </div>
          )}

          {/* Tabs */}
          <nav className="space-y-1.5">
            {[
              { id: 'overview', label: 'Overview Metrics', icon: Activity },
              ...(storedRoleIsAdmin() ? [{ id: 'affiliates', label: 'Affiliates List', icon: Users }] : []),
              { id: 'sales', label: 'Sales Management', icon: Layers },
              { id: 'withdrawals', label: 'Withdraw Payouts', icon: ArrowUpRight },
              { id: 'ledger', label: 'Double-Entry Ledger', icon: FileText },
            ].map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all text-left cursor-pointer ${
                    activeTab === tab.id 
                      ? 'bg-purple-600 text-white shadow shadow-purple-600/10' 
                      : 'text-zinc-400 hover:text-white hover:bg-[#161619]'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Action Bottom */}
        <div className="space-y-4">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-950/20 transition-all text-left cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Panel */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="h-16 border-b border-[#1f1f23] px-8 flex items-center justify-between bg-[#09090b]/80 backdrop-blur sticky top-0 z-20">
          <h2 className="text-sm font-semibold tracking-tight text-zinc-300 capitalize flex items-center gap-2">
            <span>Dashboard</span>
            <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
            <span className="text-white font-bold">{activeTab}</span>
            {storedRoleIsAdmin() && ['overview', 'sales', 'withdrawals', 'ledger'].includes(activeTab) && (
              <>
                <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
                <span className="text-zinc-500 text-xs font-semibold normal-case">Affiliate:</span>
                <select
                  value={selectedAffiliate ? selectedAffiliate.id : ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === '') {
                      selectAffiliateAndLoad(null);
                    } else {
                      const aff = affiliates.find(a => a.id === val) || users.find(u => u.id === val);
                      if (aff) {
                        selectAffiliateAndLoad(aff);
                      }
                    }
                  }}
                  className="bg-zinc-900 border border-[#1f1f23] rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-purple-500 cursor-pointer font-sans normal-case"
                >
                  <option value="">All Affiliates</option>
                  {users.filter(u => u.role === 'USER').map(u => (
                    <option key={u.id} value={u.id}>{u.name} ({u.email})</option>
                  ))}
                </select>
              </>
            )}
          </h2>

          {/* Quick Admin Actions Header Bar */}
          <div className="flex items-center gap-3">
            {storedRoleIsAdmin() && (
              <button
                onClick={triggerAdvancePayoutJob}
                disabled={jobLoading}
                className="bg-purple-600/10 hover:bg-purple-600/20 text-purple-400 border border-purple-500/20 text-xs font-semibold py-1.5 px-3 rounded-lg flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${jobLoading ? 'animate-spin' : ''}`} />
                Run Advance Job
              </button>
            )}
            
            <button
              onClick={loadAllData}
              disabled={loading}
              className="bg-[#121214] border border-[#1f1f23] hover:bg-[#161619] text-xs font-semibold py-1.5 px-3 rounded-lg flex items-center gap-2 transition-all cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </header>

        {/* Content Section */}
        <div className="p-8 space-y-8 flex-1 max-w-6xl w-full mx-auto">
          {storedRoleIsAdmin() && selectedAffiliate && !['affiliates', 'audits'].includes(activeTab) && (
            <div className="bg-purple-950/20 border border-purple-900/40 p-4 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-purple-600/20 flex items-center justify-center border border-purple-500/25">
                  <Users className="w-4.5 h-4.5 text-purple-400" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-zinc-200">
                    Inspecting Affiliate: <span className="text-purple-400">{selectedAffiliate.name}</span>
                  </h4>
                  <p className="text-[10px] text-zinc-500">
                    Showing filtered dashboard views (Sales, Ledger, Withdrawals, Stats) scoped to {selectedAffiliate.email}.
                  </p>
                </div>
              </div>
              <button
                onClick={handleClearAffiliate}
                className="bg-zinc-905 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-white text-xs font-semibold py-1.5 px-3.5 rounded-lg transition-colors cursor-pointer"
              >
                Clear Filter
              </button>
            </div>
          )}

          {loading ? (
            /* Skeletons */
            <div className="space-y-6 animate-pulse-fast">
              <div className="grid grid-cols-4 gap-5">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="h-24 bg-[#121214] border border-[#1f1f23] rounded-xl" />
                ))}
              </div>
              <div className="h-64 bg-[#121214] border border-[#1f1f23] rounded-xl" />
              <div className="h-48 bg-[#121214] border border-[#1f1f23] rounded-xl" />
            </div>
          ) : (
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.15 }}
                className="space-y-8"
              >
                {/* --- TAB 1: OVERVIEW METRICS --- */}
                {activeTab === 'overview' && (
                  <div className="space-y-8">
                    {/* Stats Counter Rows */}
                    {stats && (
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
                        {[
                          { 
                            label: 'Withdrawable Balance', 
                            val: `₹${parseFloat(stats.withdrawable_balance as any).toFixed(2)}`,
                            desc: 'Available for cash withdrawals',
                            icon: Wallet,
                            color: 'text-emerald-400 bg-emerald-950/20 border-emerald-900/30'
                          },
                          { 
                            label: 'Total Earnings', 
                            val: `₹${parseFloat(stats.total_earnings as any).toFixed(2)}`,
                            desc: 'Lifetime approved earnings',
                            icon: CheckCircle,
                            color: 'text-purple-400 bg-purple-950/20 border-purple-900/30'
                          },
                          { 
                            label: 'Pending Advance (10%)', 
                            val: `₹${parseFloat(stats.pending_advance as any).toFixed(2)}`,
                            desc: 'Advance payouts to process',
                            icon: Clock,
                            color: 'text-amber-400 bg-amber-950/20 border-amber-900/30'
                          },
                          { 
                            label: 'Total Withdrawn', 
                            val: `₹${parseFloat(stats.total_withdrawn as any).toFixed(2)}`,
                            desc: 'Completed withdrawals',
                            icon: ArrowUpRight,
                            color: 'text-blue-400 bg-blue-950/20 border-blue-900/30'
                          },
                        ].map((card, i) => {
                          const CardIcon = card.icon;
                          return (
                            <div key={i} className="bg-[#121214] border border-[#1f1f23] p-5 rounded-xl flex items-center justify-between shadow-sm">
                              <div className="space-y-1">
                                <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">{card.label}</span>
                                <h3 className="text-xl font-bold font-mono tracking-tight">{card.val}</h3>
                                <p className="text-[9px] text-zinc-500 leading-tight">{card.desc}</p>
                              </div>
                              <div className={`w-9 h-9 rounded-lg border flex items-center justify-center ${card.color}`}>
                                <CardIcon className="w-4.5 h-4.5" />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Chart & Graphics Grid */}
                    {stats && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Custom SVG Earnings Chart */}
                        <div className="bg-[#121214] border border-[#1f1f23] p-6 rounded-xl space-y-4">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-zinc-300">Earnings Projection Log</span>
                            <span className="text-[10px] text-zinc-500 font-mono">Last 7 Periods</span>
                          </div>
                          
                          {/* Mini Custom SVG Graph */}
                          <div className="h-48 w-full flex items-end justify-between pt-4 border-b border-[#1f1f23] pb-2">
                            {stats.earnings_chart.map((point, index) => {
                              const maxVal = Math.max(...stats.earnings_chart.map(p => parseFloat(p.value as any))) || 1;
                              const heightPct = (parseFloat(point.value as any) / maxVal) * 100;
                              return (
                                <div key={index} className="flex flex-col items-center gap-2 group w-full">
                                  <div className="w-8 bg-purple-600/20 hover:bg-purple-600 group-hover:shadow group-hover:shadow-purple-600/10 rounded-t-sm transition-all duration-300 relative" style={{ height: `${Math.max(heightPct, 5)}px` }}>
                                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-zinc-900 border border-zinc-800 text-[9px] text-purple-300 px-1 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none font-mono">
                                      ₹{parseFloat(point.value as any).toFixed(2)}
                                    </div>
                                  </div>
                                  <span className="text-[10px] text-zinc-500 font-semibold">{point.label}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        {/* Custom SVG Withdrawals Chart */}
                        <div className="bg-[#121214] border border-[#1f1f23] p-6 rounded-xl space-y-4">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-zinc-300">Payout Settlement Log</span>
                            <span className="text-[10px] text-zinc-500 font-mono">Last 7 Periods</span>
                          </div>
                          
                          <div className="h-48 w-full flex items-end justify-between pt-4 border-b border-[#1f1f23] pb-2">
                            {stats.withdrawals_chart.map((point, index) => {
                              const maxVal = Math.max(...stats.withdrawals_chart.map(p => parseFloat(p.value as any))) || 1;
                              const heightPct = (parseFloat(point.value as any) / maxVal) * 100;
                              return (
                                <div key={index} className="flex flex-col items-center gap-2 group w-full">
                                  <div className="w-8 bg-teal-600/20 hover:bg-teal-600 group-hover:shadow group-hover:shadow-teal-600/10 rounded-t-sm transition-all duration-300 relative" style={{ height: `${Math.max(heightPct, 5)}px` }}>
                                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-zinc-900 border border-zinc-800 text-[9px] text-teal-300 px-1 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none font-mono">
                                      ₹{parseFloat(point.value as any).toFixed(2)}
                                    </div>
                                  </div>
                                  <span className="text-[10px] text-zinc-500 font-semibold">{point.label}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* --- TAB: AFFILIATES LIST (Admin Only) --- */}
                {activeTab === 'affiliates' && storedRoleIsAdmin() && (
                  <div className="space-y-6">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#121214] border border-[#1f1f23] p-5 rounded-xl">
                      <div>
                        <h3 className="text-sm font-semibold">Affiliate Accounts</h3>
                        <p className="text-[10px] text-zinc-500 font-medium">Manage, monitor, and inspect individual affiliate performance.</p>
                      </div>

                      {/* Search & Sort Controls */}
                      <div className="flex flex-wrap items-center gap-3">
                        <div className="relative">
                          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                          <input
                            type="text"
                            placeholder="Search by name or email..."
                            className="bg-zinc-900 border border-[#1f1f23] rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500 w-52 font-sans"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                          />
                        </div>

                        <div className="flex items-center gap-2">
                          <SlidersHorizontal className="w-3.5 h-3.5 text-zinc-500" />
                          <select
                            className="bg-zinc-900 border border-[#1f1f23] rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500 cursor-pointer font-sans"
                            value={sortBy}
                            onChange={(e) => setSortBy(e.target.value)}
                          >
                            <option value="name">Sort by Name</option>
                            <option value="email">Sort by Email</option>
                            <option value="withdrawable_balance">Sort by Balance</option>
                            <option value="pending_earnings">Sort by Pending</option>
                            <option value="advance_paid">Sort by Advance Paid</option>
                          </select>
                        </div>

                        <button
                          onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
                          className="bg-zinc-900 hover:bg-zinc-850 border border-[#1f1f23] text-xs font-semibold py-1.5 px-3 rounded-lg cursor-pointer transition-colors hover:text-white text-zinc-400 font-sans"
                        >
                          {sortOrder.toUpperCase()}
                        </button>
                      </div>
                    </div>

                    <div className="bg-[#121214] border border-[#1f1f23] rounded-xl overflow-hidden shadow-sm">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-[#1f1f23] text-zinc-500 bg-[#161619] font-medium">
                            <th className="p-4">Name</th>
                            <th className="p-4">Email</th>
                            <th className="p-4 text-right">Withdrawable Balance</th>
                            <th className="p-4 text-right">Pending Earnings</th>
                            <th className="p-4 text-right">Advance Paid (Pending Sales)</th>
                            <th className="p-4 text-center">Status</th>
                            <th className="p-4 text-center">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#1f1f23]">
                          {affiliates.length === 0 ? (
                            <tr>
                              <td colSpan={7} className="p-8 text-center text-zinc-500 font-medium">No affiliate users found.</td>
                            </tr>
                          ) : (
                            affiliates.map((aff) => (
                              <tr key={aff.id} className="hover:bg-[#161619]/40 transition-colors">
                                <td className="p-4 font-bold text-zinc-200">{aff.name}</td>
                                <td className="p-4 text-zinc-400 font-mono">{aff.email}</td>
                                <td className="p-4 text-right font-mono font-bold text-emerald-400">₹{parseFloat(aff.withdrawable_balance).toFixed(2)}</td>
                                <td className="p-4 text-right font-mono font-bold text-purple-400">₹{parseFloat(aff.pending_earnings).toFixed(2)}</td>
                                <td className="p-4 text-right font-mono text-zinc-400">₹{parseFloat(aff.advance_paid).toFixed(2)}</td>
                                <td className="p-4 text-center">
                                  <span className={`inline-flex px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                                    aff.status === 'ACTIVE'
                                      ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/40'
                                      : 'bg-red-950/40 text-red-400 border border-red-900/40'
                                  }`}>
                                    {aff.status}
                                  </span>
                                </td>
                                <td className="p-4 text-center">
                                  <button
                                    onClick={() => handleSelectAffiliate(aff)}
                                    className="bg-purple-600/10 hover:bg-purple-600/20 text-purple-400 border border-purple-500/20 text-xs font-semibold py-1.5 px-3 rounded cursor-pointer transition-all"
                                  >
                                    View
                                  </button>
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* --- TAB 2: SALES MANAGEMENT --- */}
                {activeTab === 'sales' && (
                  <div className="space-y-6">
                    {/* Ingestion & Selection Control Header */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#121214] border border-[#1f1f23] p-5 rounded-xl">
                      <div>
                        <h3 className="text-sm font-semibold">Affiliate Sales Ledger</h3>
                        <p className="text-[10px] text-zinc-500">View or ingest pending sales logs here.</p>
                      </div>
                      
                      <div className="flex items-center gap-2.5">
                        <button
                          onClick={() => exportCSV(sales, "sales_ledger")}
                          className="bg-zinc-900 hover:bg-zinc-800 border border-[#1f1f23] hover:border-zinc-700 text-xs font-semibold py-1.5 px-3 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer"
                        >
                          <Download className="w-3.5 h-3.5" />
                          CSV
                        </button>

                        {storedRoleIsAdmin() && Object.keys(reconcileSelected).length > 0 && (
                          <button
                            onClick={executeReconciliation}
                            disabled={jobLoading}
                            className="bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold py-1.5 px-3 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                          >
                            <CheckSquare className="w-3.5 h-3.5" />
                            Submit Reconciliation ({Object.keys(reconcileSelected).length})
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Admin Sale Ingestion Simulator Form */}
                    {storedRoleIsAdmin() && (
                      <div className="bg-[#121214] border border-[#1f1f23] p-5 rounded-xl space-y-4">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400">Mock Sale Ingestion</h4>
                        {selectedAffiliate ? (
                          <form onSubmit={handleIngestSale} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                            <div className="space-y-1.5">
                              <label className="text-[10px] text-zinc-500 font-semibold uppercase">Brand Partner</label>
                              <input
                                type="text"
                                required
                                className="w-full bg-zinc-900 border border-[#1f1f23] rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                                placeholder="e.g. Nike, Puma, Reebok"
                                value={ingestBrand}
                                onChange={(e) => setIngestBrand(e.target.value)}
                              />
                            </div>

                            <div className="space-y-1.5">
                              <label className="text-[10px] text-zinc-500 font-semibold uppercase">Sale Amount (₹)</label>
                              <input
                                type="number"
                                required
                                className="w-full bg-zinc-900 border border-[#1f1f23] rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                                placeholder="e.g. 400"
                                value={ingestAmount}
                                onChange={(e) => setIngestAmount(e.target.value)}
                              />
                            </div>

                            <button
                              type="submit"
                              disabled={ingestLoading}
                              className="bg-purple-600 hover:bg-purple-700 disabled:bg-purple-900 text-xs font-bold py-2 px-4 rounded-lg flex items-center justify-center gap-1.5 transition-all cursor-pointer font-sans"
                            >
                              Ingest Sale for {selectedAffiliate.name}
                            </button>
                          </form>
                        ) : (
                          <p className="text-xs text-zinc-500 font-medium">
                            Please select an affiliate user from the header dropdown to ingest new sales.
                          </p>
                        )}
                      </div>
                    )}

                    {/* Sales Table */}
                    <div className="bg-[#121214] border border-[#1f1f23] rounded-xl overflow-hidden shadow-sm">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-[#1f1f23] text-zinc-500 bg-[#161619] font-medium">
                            {storedRoleIsAdmin() && <th className="p-4 w-12 text-center">Reconcile</th>}
                            <th className="p-4">External ID</th>
                            <th className="p-4">Brand</th>
                            <th className="p-4 text-right">Amount</th>
                            <th className="p-4 text-right">Earning (10%)</th>
                            <th className="p-4 text-center">Advance Payout</th>
                            <th className="p-4 text-center">Status</th>
                            <th className="p-4 text-right">Created At</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#1f1f23]">
                          {sales.length === 0 ? (
                            <tr>
                              <td colSpan={8} className="p-8 text-center text-zinc-500 font-medium">No sales recorded.</td>
                            </tr>
                          ) : (
                            sales.map((sale) => (
                              <tr key={sale.id} className="hover:bg-[#161619]/40 transition-colors">
                                {storedRoleIsAdmin() && (
                                  <td className="p-4 text-center">
                                    {sale.status === 'PENDING' ? (
                                      <div className="flex justify-center gap-1.5">
                                        <button
                                          onClick={() => {
                                            setReconcileSelected(prev => {
                                              const copy = { ...prev };
                                              if (copy[sale.id] === 'APPROVED') {
                                                delete copy[sale.id];
                                              } else {
                                                copy[sale.id] = 'APPROVED';
                                              }
                                              return copy;
                                            });
                                          }}
                                          className={`w-6 h-6 rounded flex items-center justify-center border transition-all cursor-pointer ${
                                            reconcileSelected[sale.id] === 'APPROVED'
                                              ? 'bg-emerald-600/20 border-emerald-500 text-emerald-400'
                                              : 'border-zinc-800 text-zinc-600 hover:border-zinc-600'
                                          }`}
                                          title="Approve"
                                        >
                                          ✓
                                        </button>
                                        <button
                                          onClick={() => {
                                            setReconcileSelected(prev => {
                                              const copy = { ...prev };
                                              if (copy[sale.id] === 'REJECTED') {
                                                delete copy[sale.id];
                                              } else {
                                                copy[sale.id] = 'REJECTED';
                                              }
                                              return copy;
                                            });
                                          }}
                                          className={`w-6 h-6 rounded flex items-center justify-center border transition-all cursor-pointer ${
                                            reconcileSelected[sale.id] === 'REJECTED'
                                              ? 'bg-red-600/20 border-red-500 text-red-400'
                                              : 'border-zinc-800 text-zinc-600 hover:border-zinc-600'
                                          }`}
                                          title="Reject"
                                        >
                                          ✕
                                        </button>
                                      </div>
                                    ) : (
                                      <span className="text-[10px] text-zinc-600 font-semibold">—</span>
                                    )}
                                  </td>
                                )}
                                <td className="p-4 font-mono font-bold text-zinc-300">{sale.external_id}</td>
                                <td className="p-4 capitalize">{sale.brand_name}</td>
                                <td className="p-4 text-right font-mono font-medium">₹{parseFloat(sale.amount as any).toFixed(2)}</td>
                                <td className="p-4 text-right font-mono font-bold text-purple-400">₹{parseFloat(sale.earnings as any).toFixed(2)}</td>
                                <td className="p-4 text-center">
                                  <span className={`inline-flex px-2.5 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                                    sale.advance_status === 'PAID' 
                                      ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/40' 
                                      : sale.advance_status === 'SKIPPED'
                                      ? 'bg-zinc-850 text-zinc-500 border border-zinc-800'
                                      : 'bg-amber-950/40 text-amber-400 border border-amber-900/40'
                                  }`}>
                                    {sale.advance_status}
                                  </span>
                                </td>
                                <td className="p-4 text-center">
                                  <span className={`inline-flex px-2.5 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                                    sale.status === 'APPROVED' 
                                      ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/40' 
                                      : sale.status === 'REJECTED'
                                      ? 'bg-red-950/40 text-red-400 border border-red-900/40'
                                      : 'bg-zinc-850 text-zinc-400 border border-zinc-800'
                                  }`}>
                                    {sale.status}
                                  </span>
                                </td>
                                <td className="p-4 text-right text-zinc-500">{new Date(sale.created_at).toLocaleDateString()}</td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* --- TAB 3: WITHDRAW PAYOUTS --- */}
                {activeTab === 'withdrawals' && (
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                    {/* Form block: Standard User Only */}
                    {!storedRoleIsAdmin() && (
                      <div className="bg-[#121214] border border-[#1f1f23] p-6 rounded-xl space-y-6 lg:col-span-1">
                        <div>
                          <h3 className="text-sm font-semibold">Request Settlement</h3>
                          <p className="text-[10px] text-zinc-500">Initiate a withdrawable balance payout transfer.</p>
                        </div>

                        {/* Cooldown Alert Banner */}
                        <div className="bg-amber-950/20 border border-amber-900/40 p-3.5 rounded-lg flex gap-3 text-xs text-amber-300">
                          <AlertCircle className="w-5 h-5 flex-shrink-0 text-amber-400" />
                          <div>
                            <span className="font-semibold block mb-0.5">24h Cooldown Protection</span>
                            Withdrawals are strictly constrained to one successful payout execution every 24 hours.
                          </div>
                        </div>

                        <form onSubmit={handleWithdrawalRequest} className="space-y-4">
                          <div className="space-y-1.5">
                            <label className="text-[10px] text-zinc-500 font-semibold uppercase">Amount (INR)</label>
                            <div className="relative">
                              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500 text-xs font-semibold">₹</span>
                              <input
                                type="number"
                                required
                                className="w-full bg-zinc-900 border border-[#1f1f23] rounded-lg pl-8 pr-4 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500 font-mono"
                                placeholder="e.g. 100.00"
                                value={withdrawAmount}
                                onChange={(e) => setWithdrawAmount(e.target.value)}
                              />
                            </div>
                          </div>

                          <button
                            type="submit"
                            disabled={withdrawLoading}
                            className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-900 text-xs font-bold py-3 px-4 rounded-lg flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                          >
                            {withdrawLoading ? 'Processing...' : 'Initiate Withdrawal'}
                            <ArrowUpRight className="w-4 h-4" />
                          </button>
                        </form>
                      </div>
                    )}

                    {/* Withdrawal Request logs */}
                    <div className={`bg-[#121214] border border-[#1f1f23] p-6 rounded-xl space-y-6 ${storedRoleIsAdmin() ? 'lg:col-span-3' : 'lg:col-span-2'}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-sm font-semibold">{storedRoleIsAdmin() ? "Withdrawal Requests Manager" : "Withdrawal History"}</h3>
                          <p className="text-[10px] text-zinc-500 font-medium">Logs and gateway callback trackers.</p>
                        </div>
                        <button
                          onClick={() => exportCSV(withdrawals, "withdrawals_history")}
                          className="bg-zinc-900 hover:bg-zinc-800 border border-[#1f1f23] hover:border-zinc-700 text-xs font-semibold py-1.5 px-3 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer"
                        >
                          <Download className="w-3.5 h-3.5" />
                          CSV
                        </button>
                      </div>

                      <div className="overflow-x-auto border border-[#1f1f23] rounded-lg">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="border-b border-[#1f1f23] text-zinc-500 bg-[#161619] font-medium">
                              <th className="p-4">Withdrawal ID</th>
                              {storedRoleIsAdmin() && <th className="p-4">Affiliate</th>}
                              <th className="p-4 text-right">Amount</th>
                              <th className="p-4 text-center">Status</th>
                              {storedRoleIsAdmin() && <th className="p-4 text-right">Available Balance</th>}
                              <th className="p-4">Gateway Feedback</th>
                              <th className="p-4 text-right">Created At</th>
                              {storedRoleIsAdmin() && <th className="p-4 text-center">Actions</th>}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#1f1f23]">
                            {withdrawals.length === 0 ? (
                              <tr>
                                <td colSpan={storedRoleIsAdmin() ? 8 : 5} className="p-8 text-center text-zinc-500 font-medium">No withdrawal requests found.</td>
                              </tr>
                            ) : (
                              withdrawals.map((w) => {
                                const affiliate = affiliates.find(a => a.id === w.user_id);
                                return (
                                  <tr key={w.id} className="hover:bg-[#161619]/40 transition-colors">
                                    <td className="p-4 font-mono text-zinc-400 font-semibold">{w.id.slice(0, 8)}...</td>
                                    {storedRoleIsAdmin() && (
                                      <td className="p-4">
                                        <div className="font-bold text-zinc-200">{affiliate?.name || 'Unknown'}</div>
                                        <div className="text-[10px] text-zinc-500 font-mono">{affiliate?.email}</div>
                                      </td>
                                    )}
                                    <td className="p-4 text-right font-mono font-bold text-zinc-300">₹{parseFloat(w.amount as any).toFixed(2)}</td>
                                    <td className="p-4 text-center">
                                      <span className={`inline-flex px-2.5 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                                        w.status === 'COMPLETED' 
                                          ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/40' 
                                          : w.status === 'FAILED'
                                          ? 'bg-red-950/40 text-red-400 border border-red-900/40'
                                          : 'bg-zinc-850 text-zinc-400 border border-zinc-800'
                                      }`}>
                                        {w.status}
                                      </span>
                                    </td>
                                    {storedRoleIsAdmin() && (
                                      <td className="p-4 text-right font-mono text-zinc-400 font-bold">
                                        ₹{parseFloat(affiliate?.withdrawable_balance || 0).toFixed(2)}
                                      </td>
                                    )}
                                    <td className="p-4 text-zinc-400 italic max-w-xs truncate">{w.failure_reason || 'No errors logged.'}</td>
                                    <td className="p-4 text-right text-zinc-500">{new Date(w.created_at).toLocaleString()}</td>
                                    {storedRoleIsAdmin() && (
                                      <td className="p-4 text-center">
                                        {w.status === 'PENDING' || w.status === 'PROCESSING' ? (
                                          <div className="flex justify-center gap-1.5">
                                            <button
                                              onClick={() => handleSimulateWebhookResult(w.id, 'COMPLETED')}
                                              className="bg-emerald-900/20 hover:bg-emerald-800 border border-emerald-700/30 text-emerald-400 text-[10px] font-bold px-2 py-1 rounded cursor-pointer transition-colors"
                                            >
                                              Approve
                                            </button>
                                            <button
                                              onClick={() => handleSimulateWebhookResult(w.id, 'FAILED')}
                                              className="bg-red-900/20 hover:bg-red-800 border border-red-700/30 text-red-400 text-[10px] font-bold px-2 py-1 rounded cursor-pointer transition-colors"
                                            >
                                              Reject
                                            </button>
                                          </div>
                                        ) : (
                                          <span className="text-[10px] text-zinc-600 font-semibold">—</span>
                                        )}
                                      </td>
                                    )}
                                  </tr>
                                );
                              })
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}

                {/* --- TAB 4: DOUBLE-ENTRY LEDGER --- */}
                {activeTab === 'ledger' && (
                  <div className="bg-[#121214] border border-[#1f1f23] p-6 rounded-xl space-y-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-sm font-semibold">Balanced Double-Entry General Ledger</h3>
                        <p className="text-[10px] text-zinc-500 font-medium">The immutable source of truth: debits equal credits.</p>
                      </div>
                      <button
                        onClick={() => exportCSV(ledger, "general_ledger")}
                        className="bg-zinc-900 hover:bg-zinc-800 border border-[#1f1f23] hover:border-zinc-700 text-xs font-semibold py-1.5 px-3 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer"
                      >
                        <Download className="w-3.5 h-3.5" />
                        CSV
                      </button>
                    </div>

                    <div className="overflow-x-auto border border-[#1f1f23] rounded-lg">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-[#1f1f23] text-zinc-500 bg-[#161619] font-medium">
                            <th className="p-4">Timestamp</th>
                            <th className="p-4">Transaction Group</th>
                            <th className="p-4">Ledger Account</th>
                            <th className="p-4">Movement Type</th>
                            <th className="p-4 text-right">Debit (Charge)</th>
                            <th className="p-4 text-right">Credit (Credit)</th>
                            <th className="p-4">Reference</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#1f1f23] font-mono">
                          {ledger.length === 0 ? (
                            <tr>
                              <td colSpan={7} className="p-8 text-center text-zinc-500 font-medium font-sans">No ledger entries.</td>
                            </tr>
                          ) : (
                            ledger.map((entry) => {
                              const isDebit = parseFloat(entry.debit as any) > 0;
                              return (
                                <tr key={entry.id} className="hover:bg-[#161619]/40 transition-colors">
                                  <td className="p-4 text-zinc-500 text-[10px]">{new Date(entry.created_at).toLocaleString()}</td>
                                  <td className="p-4 text-zinc-400 font-semibold">{entry.transaction_group_id.slice(0, 8)}...</td>
                                  <td className="p-4">
                                    <span className={`inline-flex px-1.5 py-0.5 rounded text-[9px] font-extrabold uppercase ${
                                      entry.balance_type === 'WITHDRAWABLE'
                                        ? 'bg-purple-950/20 text-purple-400 border border-purple-900/30'
                                        : 'bg-zinc-900 text-zinc-400 border border-zinc-800'
                                    }`}>
                                      {entry.balance_type}
                                    </span>
                                  </td>
                                  <td className="p-4 text-[10px] text-zinc-300 font-semibold">{entry.transaction_type}</td>
                                  <td className="p-4 text-right font-bold text-red-400">
                                    {isDebit ? `₹${parseFloat(entry.debit as any).toFixed(4)}` : '—'}
                                  </td>
                                  <td className="p-4 text-right font-bold text-emerald-400">
                                    {!isDebit ? `₹${parseFloat(entry.credit as any).toFixed(4)}` : '—'}
                                  </td>
                                  <td className="p-4 text-zinc-500 text-[10px] capitalize font-sans">{entry.reference_type.toLowerCase()} ({entry.reference_id.slice(0, 6)})</td>
                                </tr>
                              );
                            })
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

              </motion.div>
            </AnimatePresence>
          )}
        </div>
      </main>

      {/* Toast notifications drawer */}
      <div className="fixed bottom-6 right-6 z-50 space-y-3 pointer-events-none max-w-sm w-full">
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, y: 30, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className={`pointer-events-auto p-4 rounded-xl shadow-lg border flex items-start gap-3 w-full ${
              toast.type === 'success'
                ? 'bg-emerald-950/95 border-emerald-900/60 text-emerald-300'
                : toast.type === 'error'
                ? 'bg-red-950/95 border-red-900/60 text-red-300'
                : 'bg-[#121214]/95 border-[#1f1f23]/60 text-zinc-200'
            }`}
          >
            <div className="mt-0.5">
              {toast.type === 'success' ? (
                <CheckCircle className="w-4 h-4 text-emerald-400" />
              ) : toast.type === 'error' ? (
                <XCircle className="w-4 h-4 text-red-400" />
              ) : (
                <AlertCircle className="w-4 h-4 text-purple-400" />
              )}
            </div>
            <div className="text-xs leading-relaxed font-semibold">{toast.message}</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
