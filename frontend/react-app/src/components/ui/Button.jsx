import styles from './Button.module.css';

export function Button({ variant = 'secondary', size = 'md', children, onClick, disabled, type = 'button', className = '' }) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`${styles.btn} ${styles[variant]} ${styles[size]} ${className}`}
    >
      {children}
    </button>
  );
}

