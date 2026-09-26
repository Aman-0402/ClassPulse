import { useState } from "react";

interface AvatarProps {
  src?: string | null;
  name: string;
  size: number;
  rounded?: "circle" | "square";
  className?: string;
}

// A student photo, or their initial if there's no photo - or if the photo URL
// 404s. Old students photographed before a server move/cleanup can end up with
// a DB row pointing at a file that's no longer on disk; without this, that
// showed the browser's broken-image icon everywhere the photo was used.
export default function Avatar({ src, name, size, rounded = "circle", className }: AvatarProps) {
  const [broken, setBroken] = useState(false);

  if (src && !broken) {
    return (
      <img
        src={src}
        alt=""
        width={size}
        height={size}
        className={className}
        style={{
          borderRadius: rounded === "circle" ? "50%" : "12px",
          objectFit: "cover",
          border: "2px solid var(--line)",
          flexShrink: 0,
        }}
        onError={() => setBroken(true)}
      />
    );
  }

  return (
    <span
      className={`d-inline-flex align-items-center justify-content-center flex-shrink-0 ${className ?? ""}`}
      style={{
        width: size,
        height: size,
        borderRadius: rounded === "circle" ? "50%" : "12px",
        background: "var(--line)",
        color: "var(--ink-soft)",
        fontWeight: 700,
        fontSize: size * 0.4,
      }}
    >
      {(name || "?").charAt(0).toUpperCase()}
    </span>
  );
}
