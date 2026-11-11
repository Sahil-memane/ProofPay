import styles from './Badge.module.css';

const variantMap = {
  success: styles.success,
  warning: styles.warning,
  danger:  styles.danger,
  info:    styles.info,
  neutral: styles.neutral,
};

export function Badge({ variant = 'neutral', children }) {
  return <span className={`${styles.badge} ${variantMap[variant] ?? styles.neutral}`}>{children}</span>;
}

/** Map backend state strings to badge variants */
export function stateBadge(state) {
  if (!state) return 'neutral';
  const s = state.toUpperCase();
  if (['RECOVERED', 'PAID_ELSEWHERE', 'FUNDED', 'COMPLETED', 'RELEASED', 'APPROVED', 'BOTH_APPROVED'].some(v => s.includes(v))) return 'success';
  if (['HALTED', 'FAILED', 'DISPUTED', 'DENIED', 'REJECTED'].some(v => s.includes(v))) return 'danger';
  if (['ACTIVE', 'PENDING', 'AWAITING', 'DRAFT', 'HUMAN_REVIEW', 'OPEN'].some(v => s.includes(v))) return 'warning';
  if (['INFO', 'REVIEW'].some(v => s.includes(v))) return 'info';
  return 'neutral';
}

