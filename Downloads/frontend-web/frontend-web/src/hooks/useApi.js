/**
 * useApi — central data hook for TYE
 * Connects the Dashboard to all existing FastAPI backend routes.
 * Keeps Savings Goals & Categories in sessionStorage (no backend endpoint yet).
 */
import { useState, useCallback, useEffect } from 'react';
import axios from 'axios';

const API = 'http://127.0.0.1:8000';

// Timezone-safe YYYY-MM string
function toYM(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

export function useApi(userId) {
  const [transactions, setTransactions] = useState([]);
  const [budgets, setBudgets]           = useState([]);
  const [summary, setSummary]           = useState({ total_spent: 0, breakdown: {} });
  const [loading, setLoading]           = useState(false);

  // sessionStorage-backed savings & categories (no backend yet)
  const [savings, setSavingsRaw] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem(`tye_savings_${userId}`) || '[]'); } catch { return []; }
  });
  const [cats, setCatsRaw] = useState(() => {
    try {
      const stored = sessionStorage.getItem(`tye_cats_${userId}`);
      return stored ? JSON.parse(stored) : ['Food','Transport','Rent','Utilities','Shopping','Entertainment'];
    } catch { return ['Food','Transport','Rent','Utilities','Shopping','Entertainment']; }
  });

  const setSavings = useCallback(updater => {
    setSavingsRaw(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      sessionStorage.setItem(`tye_savings_${userId}`, JSON.stringify(next));
      return next;
    });
  }, [userId]);

  const setCats = useCallback(updater => {
    setCatsRaw(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      sessionStorage.setItem(`tye_cats_${userId}`, JSON.stringify(next));
      return next;
    });
  }, [userId]);

  // ── Transactions ────────────────────────────────────────────────────────────
  const fetchTransactions = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/transactions/${userId}`);
      setTransactions(res.data);
    } catch (e) { console.error('fetchTransactions', e); }
  }, [userId]);

  // ── Summary ─────────────────────────────────────────────────────────────────
  const fetchSummary = useCallback(async (month) => {
    const m = month || toYM(new Date());
    try {
      const res = await axios.get(`${API}/summary/${userId}?month=${m}`);
      setSummary(res.data);
    } catch (e) { console.error('fetchSummary', e); }
  }, [userId]);

  // ── Budgets ─────────────────────────────────────────────────────────────────
  const fetchBudgets = useCallback(async (month) => {
    const m = month || toYM(new Date());
    try {
      const res = await axios.get(`${API}/budgets/${userId}/${m}`);
      setBudgets(res.data);
    } catch (e) { console.error('fetchBudgets', e); }
  }, [userId]);

  // ── Initial load ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!userId) return;
    const m = toYM(new Date());
    fetchTransactions();
    fetchSummary(m);
    fetchBudgets(m);
  }, [userId, fetchTransactions, fetchSummary, fetchBudgets]);

  // ── Mutation helpers ─────────────────────────────────────────────────────────

  const addTransaction = useCallback(async ({ amount, category, description, date }) => {
    const res = await axios.post(`${API}/transactions/`, {
      amount: parseFloat(amount), category, description, date, user_id: userId,
    });
    await fetchTransactions();
    await fetchSummary(date.slice(0, 7));
    return res.data;
  }, [userId, fetchTransactions, fetchSummary]);

  const deleteTransaction = useCallback(async (id, month) => {
    await axios.delete(`${API}/transactions/${id}`);
    await fetchTransactions();
    if (month) await fetchSummary(month);
  }, [fetchTransactions, fetchSummary]);

  const updateTransaction = useCallback(async (id, fields, month) => {
    await axios.put(`${API}/transactions/${id}`, fields);
    await fetchTransactions();
    if (month) await fetchSummary(month);
  }, [fetchTransactions, fetchSummary]);

  const createBudget = useCallback(async ({ category, monthly_limit, month, alert_threshold }) => {
    const m = month || toYM(new Date());
    await axios.post(`${API}/budgets/?user_id=${userId}`, {
      category, monthly_limit: parseFloat(monthly_limit), month: m,
      alert_threshold: parseInt(alert_threshold) || 80, notifications_enabled: true,
    });
    await fetchBudgets(m);
  }, [userId, fetchBudgets]);

  const deleteBudget = useCallback(async (id, month) => {
    await axios.delete(`${API}/budgets/${id}`);
    await fetchBudgets(month || toYM(new Date()));
  }, [fetchBudgets]);

  const updateBudget = useCallback(async (id, fields, month) => {
    await axios.put(`${API}/budgets/${id}`, fields);
    await fetchBudgets(month || toYM(new Date()));
  }, [fetchBudgets]);

  const fetchMonthlyReport = useCallback(async (month) => {
    const res = await axios.get(`${API}/monthly-report/${userId}?month=${month}`);
    return res.data;
  }, [userId]);

  return {
    // data
    transactions, budgets, summary, loading,
    savings, cats,
    // setters
    setSavings, setCats,
    // fetchers
    fetchTransactions, fetchSummary, fetchBudgets, fetchMonthlyReport,
    // mutations
    addTransaction, deleteTransaction, updateTransaction,
    createBudget, deleteBudget, updateBudget,
    // util
    toYM,
  };
}
