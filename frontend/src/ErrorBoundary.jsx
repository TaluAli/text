import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    // Log safe info to console without exposing secrets
    console.error('UI error boundary caught', { message: error?.message, info })
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
    if (this.props.onReset) {
      this.props.onReset()
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-fallback">
          <div className="glass-card">
            <h2>Something went wrong</h2>
            <p>{this.state.error?.message || 'Unexpected error occurred.'}</p>
            <button onClick={this.handleRetry}>Try again</button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
