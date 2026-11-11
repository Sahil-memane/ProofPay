import { useEffect } from 'react';
import styles from './Drawer.module.css';
import { Button } from './Button';

export function Drawer({ open, onClose, title, children, width = 480 }) {
  useEffect(() => {
    if (open) document.body.style.overflow = 'hidden';
    else document.body.style.overflow = '';
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  if (!open) return null;

  return (
    <>
      <div className={styles.backdrop} onClick={onClose} />
      <div className={styles.drawer} style={{ width }}>
        <div className={styles.header}>
          <span className={styles.title}>{title}</span>
          <Button variant="ghost" size="sm" onClick={onClose}>✕</Button>
        </div>
        <div className={styles.body}>{children}</div>
      </div>
    </>
  );
}

