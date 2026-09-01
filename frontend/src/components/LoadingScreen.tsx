import FourSquare from "react-loading-indicators/FourSquare";

// Centered loading state, reused everywhere a page is waiting on its first
// fetch (or, via App.tsx's Suspense fallback, waiting on its own JS chunk to
// load) — one consistent look instead of a spinner stuck at the top-left of
// whatever container happened to render it. Colors are shades of the app's
// own purple palette (index.css), not the package's rainbow default, to stay
// on the monochromatic theme.
export default function LoadingScreen() {
  return (
    <div
      className="d-flex flex-column align-items-center justify-content-center gap-3"
      style={{ minHeight: "60vh" }}
    >
      <FourSquare color={["#3c1e5e", "#7c3fae", "#9d5fd1", "#c9a3e8"]} text="Loading" textColor="#6e6280" />
    </div>
  );
}
