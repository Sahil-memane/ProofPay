import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { DemoBar } from './DemoBar';
import { usePageMeta } from '../../hooks/usePageMeta';
import styles from './AppShell.module.css';

export function AppShell() {
  const { title, sub } = usePageMeta();

  return (
    <div className={styles.shell}>
      <Sidebar />
      <div className={styles.main}>
        <Header title={title} subtitle={sub} />
        <main className={styles.content}>
          <Outlet />
        </main>
        <DemoBar />
      </div>
    </div>
  );
}
