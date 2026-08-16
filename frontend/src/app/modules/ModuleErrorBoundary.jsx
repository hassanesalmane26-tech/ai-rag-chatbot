import { Component } from "react";

export default class ModuleErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return <section className="empty-state" role="alert"><h2>Module indisponible</h2><p>TRIDENT n’a pas pu ouvrir ce module.</p><button type="button" onClick={() => this.setState({ failed: false })}>Réessayer</button></section>;
    }
    return this.props.children;
  }
}
