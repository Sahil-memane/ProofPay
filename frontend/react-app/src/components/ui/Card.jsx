import styles from './Card.module.css';

export function Card({ children, style, className = '', noPadding = false }) {
  return (
    <div className={`${styles.card} ${noPadding ? styles.noPadding : ''} ${className}`} style={style}>
      {children}
    </div>
  );
}

