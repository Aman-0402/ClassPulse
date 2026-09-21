// Centered loading state, reused everywhere a page is waiting on its first
// fetch (or, via App.tsx's Suspense fallback, waiting on its own JS chunk to
// load). A CSS-3D spinning QR cube - pure CSS, no extra dependency.

// Finder-pattern-ish 5x5 layouts so each face reads as a QR code.
const FACES: Record<string, string> = {
  front: "1111110001101011000111111",
  back: "1010101110010010111010101",
  right: "1101110101001001010111011",
  left: "0110111011110110111001100",
  top: "1110110101111010101101110",
  bottom: "1011101010010011010110101",
};

export default function LoadingScreen() {
  return (
    <div className="loading-screen" role="status" aria-live="polite" aria-label="Loading ClassPulse">
      <div className="l3d-scene">
        <div className="l3d-stage" aria-hidden="true">
          <div className="l3d-rings">
            <span />
            <span />
            <span />
          </div>
          <div className="l3d-cube">
            {Object.entries(FACES).map(([name, bits]) => (
              <div key={name} className={`l3d-face l3d-${name}`}>
                {bits.split("").map((bit, i) => (
                  <i key={i} className={bit === "1" ? "on" : ""} />
                ))}
              </div>
            ))}
          </div>
          <div className="l3d-shadow" />
        </div>
        <div>
          <p className="l3d-title">ClassPulse</p>
          <p className="l3d-text">Syncing attendance</p>
          <div className="l3d-dots" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>
    </div>
  );
}
