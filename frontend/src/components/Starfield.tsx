// Extra star layer + shooting stars for .auth-shell — the two base twinkling
// layers are plain CSS pseudo-elements (::before/::after on .auth-shell in
// index.css), but a page only gets one of each, so this covers the third
// (larger) layer and the shooting-star streaks as real DOM nodes instead.
const SHOOTING_STARS = [
  { top: "12%", left: "70%", duration: "6s", delay: "0s" },
  { top: "28%", left: "20%", duration: "9s", delay: "3s" },
  { top: "55%", left: "85%", duration: "13s", delay: "6.5s" },
];

export default function Starfield() {
  return (
    <>
      <div className="starfield-large" />
      {SHOOTING_STARS.map((star, i) => (
        <span
          key={i}
          className="shooting-star"
          style={{
            top: star.top,
            left: star.left,
            animationDuration: star.duration,
            animationDelay: star.delay,
          }}
        />
      ))}
    </>
  );
}
