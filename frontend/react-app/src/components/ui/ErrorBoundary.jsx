import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ProofPay UI ErrorBoundary caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
          background: 'radial-gradient(1100px 600px at 12% -10%, #0A4BBD 0%, transparent 60%), radial-gradient(900px 520px at 100% 110%, #0070E0 0%, transparent 55%), #003087',
          color: '#ffffff',
          fontFamily: 'Inter, -apple-system, sans-serif',
          textAlign: 'center',
        }}>
          <div style={{
            background: '#ffffff',
            color: '#172B4D',
            padding: '36px 32px',
            borderRadius: 16,
            maxWidth: 520,
            width: '100%',
            boxShadow: '0 24px 70px rgba(0, 12, 48, 0.5)',
          }}>
            <div style={{ width: 44, height: 44, borderRadius: 10, background: '#0070E0', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />
                <path d="M9 12l2 2 4-4" />
              </svg>
            </div>
            <h2 style={{ margin: '0 0 8px', color: '#003087', fontSize: 22, fontWeight: 600 }}>ProofPay Workspace Notice</h2>
            <p style={{ color: '#64748B', fontSize: 14, margin: '0 0 24px', lineHeight: 1.5 }}>
              {this.state.error?.message || 'A navigation or module refresh occurred. Reload to restore session.'}
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button
                type="button"
                onClick={() => window.location.reload()}
                style={{
                  padding: '10px 22px',
                  borderRadius: 8,
                  border: 'none',
                  background: '#0070E0',
                  color: '#fff',
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Reload
              </button>
              <button
                type="button"
                onClick={() => { window.location.href = '/'; }}
                style={{
                  padding: '10px 22px',
                  borderRadius: 8,
                  border: '1px solid #E5E9F0',
                  background: '#fff',
                  color: '#172B4D',
                  fontSize: 14,
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                Back to Home
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

