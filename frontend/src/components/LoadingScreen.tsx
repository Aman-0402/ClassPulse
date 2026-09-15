import logo from "../assets/logo.png";

// Centered loading state, reused everywhere a page is waiting on its first
// fetch (or, via App.tsx's Suspense fallback, waiting on its own JS chunk to
// load) - one consistent look instead of a spinner stuck at the top-left of
// whatever container happened to render it.
export default function LoadingScreen() {
  return (
    <div className="loading-screen" role="status" aria-live="polite" aria-label="Loading ClassPulse">
      <div className="loading-orbit" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>

      <div className="loading-card">
        <img className="loading-logo" src={logo} alt="" />
        <div className="loading-qr" aria-hidden="true">
          {Array.from({ length: 25 }).map((_, index) => (
            <span key={index} style={{ animationDelay: `${(index % 7) * 0.09}s` }} />
          ))}
          <div className="loading-scan-line" />
        </div>
        <p className="loading-title">ClassPulse</p>
        <p className="loading-text">Syncing attendance</p>
        <div className="loading-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  );
}
