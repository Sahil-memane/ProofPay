import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { usePageMeta } from '../../hooks/usePageMeta';
import { useAuth } from '../../hooks/useAuth';
import styles from './AppShell.module.css';

export function AppShell() {
  const { title, sub } = usePageMeta();
  const { isAuthenticated, canAccess } = useAuth();
  const location = useLocation();

  // If not authenticated, require login first
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If logged in but route is outside role permissions, redirect to /dashboard
  if (!canAccess(location.pathname)) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className={styles.shell}>
      <Sidebar />
      <div className={styles.main}>
        <Header title={title} subtitle={sub} />
        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
