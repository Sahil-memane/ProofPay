import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { DemoBar } from './DemoBar';
import styles from './AppShell.module.css';

export function AppShell({ title, subtitle }) {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <div className={styles.main}>
        <Header title={title} subtitle={subtitle} />
        <main className={styles.content}>
          <Outlet />
        </main>
        <DemoBar />
      </div>
    </div>
  );
}

