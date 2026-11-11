import styles from './Spinner.module.css';

export function Spinner({ size = 24 }) {
  return <div className={styles.spin} style={{ width: size, height: size }} aria-label="Loading" />;
}

export function PageLoader() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
      <Spinner size={40} />
    </div>
  );
}

