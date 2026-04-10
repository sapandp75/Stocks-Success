import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo })
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '2rem', backgroundColor: '#fef2f2', border: '2px solid #e5484d', borderRadius: '8px', margin: '2rem' }}>
          <h2 style={{ color: '#e5484d', marginBottom: '1rem' }}>Something crashed</h2>
          <pre style={{ fontSize: '13px', whiteSpace: 'pre-wrap', color: '#1a1a2e' }}>
            {this.state.error?.toString()}
          </pre>
          <details style={{ marginTop: '1rem' }}>
            <summary style={{ cursor: 'pointer', color: '#6b7280' }}>Component stack</summary>
            <pre style={{ fontSize: '11px', whiteSpace: 'pre-wrap', color: '#6b7280', marginTop: '0.5rem' }}>
              {this.state.errorInfo?.componentStack}
            </pre>
          </details>
          <button
            onClick={() => { this.setState({ hasError: false, error: null, errorInfo: null }) }}
            style={{ marginTop: '1rem', padding: '0.5rem 1rem', backgroundColor: '#00a562', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Try Again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
