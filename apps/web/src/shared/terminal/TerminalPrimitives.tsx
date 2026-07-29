import type { ReactNode } from "react";

function classes(...values: Array<string | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function TerminalPageHeader({ eyebrow, title, description, actions, className }: {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
}) {
  return <header className={classes("terminal-page-header", className)}>
    <div className="terminal-page-header-copy">
      <p className="terminal-page-eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      {description && <p className="terminal-page-description">{description}</p>}
    </div>
    {actions && <div className="terminal-page-header-actions">{actions}</div>}
  </header>;
}

export function TerminalStatusStrip({ ariaLabel, children, className }: {
  ariaLabel: string;
  children: ReactNode;
  className?: string;
}) {
  return <section className={classes("terminal-status-strip", className)} aria-label={ariaLabel}>{children}</section>;
}

export function TerminalMetricBand({ ariaLabel, children, className }: {
  ariaLabel: string;
  children: ReactNode;
  className?: string;
}) {
  return <section className={classes("terminal-metric-band", className)} aria-label={ariaLabel}>{children}</section>;
}

export function TerminalPanel({ title, subtitle, headerAside, ariaLabel, children, className, bodyClassName }: {
  title: string;
  subtitle?: string;
  headerAside?: ReactNode;
  ariaLabel: string;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return <section className={classes("terminal-panel", className)} aria-label={ariaLabel}>
    <header className="terminal-panel-header">
      <div className="terminal-panel-heading">
        <strong className="terminal-panel-title">{title}</strong>
        {subtitle && <span className="terminal-panel-subtitle">{subtitle}</span>}
      </div>
      {headerAside}
    </header>
    <div className={classes("terminal-panel-body", bodyClassName)}>{children}</div>
  </section>;
}

export type TerminalState = "loading" | "ready" | "partial" | "stale" | "error" | "unavailable";

export function TerminalStateNotice({ state, title, detail, icon, className }: {
  state: TerminalState;
  title: string;
  detail?: string;
  icon?: ReactNode;
  className?: string;
}) {
  return <div className={classes("terminal-state-notice", className)} data-state={state} role="status">
    {icon ?? <i aria-hidden="true" />}
    <strong>{title}</strong>
    {detail && <span>{detail}</span>}
  </div>;
}
