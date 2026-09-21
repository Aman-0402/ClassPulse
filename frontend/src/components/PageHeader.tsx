import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  // Small line above the title (e.g. "Student" / "Teacher"), for orientation.
  eyebrow?: string;
  // Right-aligned controls: buttons, filters, a badge.
  actions?: ReactNode;
}

// One consistent page title block for every authenticated screen.
export default function PageHeader({ title, subtitle, eyebrow, actions }: PageHeaderProps) {
  return (
    <header className="pg-head">
      <div className="pg-head-text">
        {eyebrow && <div className="pg-eyebrow">{eyebrow}</div>}
        <h1 className="pg-title">{title}</h1>
        {subtitle && <p className="pg-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="pg-actions">{actions}</div>}
    </header>
  );
}
