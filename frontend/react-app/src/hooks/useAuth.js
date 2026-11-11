import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Normalizes role to one of: 'client' | 'freelancer' | 'merchant' | 'admin'
 */
export function normalizeRole(role) {
  if (!role) return 'client';
  const r = String(role).toLowerCase();
  if (r.includes('admin') || r.includes('risk')) return 'admin';
  if (r.includes('free') || r.includes('contractor') || r.includes('dev')) return 'freelancer';
  if (r.includes('merch') || r.includes('bill')) return 'merchant';
  return 'client';
}

export function getStoredSession() {
  try {
    const raw = sessionStorage.getItem('pp_session') || localStorage.getItem('pp_session');
    if (!raw) return null;
    const session = JSON.parse(raw);
    if (!session || !session.user) return null;
    return {
      user: session.user,
      token: session.token || 'demo-token',
      role: normalizeRole(session.user.role || session.role),
      offline: !!session.offline,
    };
  } catch (_) {
    return null;
  }
}

// Role-to-route permissions map
export const ROLE_PERMISSIONS = {
  client: [
    '/dashboard',
    '/projects',
    '/project-details',
    '/create-project-wizard',
    '/milestones',
    '/approvals',
    '/invoices',
    '/disputes',
    '/pay',
    '/assistant',
    '/settings',
    '/help',
  ],
  freelancer: [
    '/dashboard',
    '/projects',
    '/project-details',
    '/milestones',
    '/submissions',
    '/ledger',
    '/reputation',
    '/disputes',
    '/assistant',
    '/settings',
    '/help',
  ],
  merchant: [
    '/dashboard',
    '/invoices',
    '/cases',
    '/recovery-overview',
    '/payment-attempts',
    '/reconciliation',
    '/disputes',
    '/ledger',
    '/pay',
    '/analytics',
    '/audit',
    '/integrations',
    '/settings',
    '/help',
  ],
  admin: [
    '/dashboard',
    '/projects',
    '/project-details',
    '/create-project-wizard',
    '/milestones',
    '/submissions',
    '/ledger',
    '/recovery-overview',
    '/cases',
    '/invoices',
    '/payment-attempts',
    '/reconciliation',
    '/disputes',
    '/mandate-guard',
    '/reputation',
    '/approvals',
    '/agents',
    '/analytics',
    '/audit',
    '/assistant',
    '/pay',
    '/integrations',
    '/settings',
    '/help',
  ],
};

export function canAccessRoute(role, path) {
  const normRole = normalizeRole(role);
  const allowed = ROLE_PERMISSIONS[normRole] || ROLE_PERMISSIONS.client;
  // If path is root or matches allowed list
  return allowed.some(p => path === p || path.startsWith(p + '/'));
}

export function useAuth() {
  const [session, setSession] = useState(getStoredSession);
  const navigate = useNavigate();

  useEffect(() => {
    const handleAuthChange = () => {
      setSession(getStoredSession());
    };

    window.addEventListener('storage', handleAuthChange);
    window.addEventListener('authChanged', handleAuthChange);
    return () => {
      window.removeEventListener('storage', handleAuthChange);
      window.removeEventListener('authChanged', handleAuthChange);
    };
  }, []);

  const login = useCallback((userData, token = 'token', remember = true) => {
    const role = normalizeRole(userData.role);
    const s = {
      user: { ...userData, role },
      token,
      role,
    };
    const storage = remember ? localStorage : sessionStorage;
    storage.setItem('pp_session', JSON.stringify(s));
    sessionStorage.setItem('pp_role', role);
    localStorage.setItem('proofpay_role', role);
    setSession(s);
    window.dispatchEvent(new Event('authChanged'));
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('pp_session');
    sessionStorage.removeItem('pp_session');
    sessionStorage.removeItem('pp_role');
    localStorage.removeItem('proofpay_role');
    setSession(null);
    window.dispatchEvent(new Event('authChanged'));
    navigate('/login');
  }, [navigate]);

  return {
    isAuthenticated: !!session,
    user: session?.user ?? null,
    role: session ? normalizeRole(session.role) : 'client',
    session,
    login,
    logout,
    canAccess: (path) => canAccessRoute(session?.role, path),
  };
}

