import type { CSSProperties } from "react";

export function Icon({ name, size = 18, style }: { name: "search" | "sliders" | "arrow" | "plus" | "close" | "grid" | "cube" | "pin" | "check" | "chevron" | "refresh" | "expand" | "layers"; size?: number; style?: CSSProperties }) {
  const paths = {
    search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4 4" /></>,
    sliders: <><path d="M4 6h4m4 0h8M4 12h10m4 0h2M4 18h2m4 0h10" /><circle cx="10" cy="6" r="2" /><circle cx="16" cy="12" r="2" /><circle cx="8" cy="18" r="2" /></>,
    arrow: <><path d="M5 19 19 5M5 5h14v14" /></>,
    plus: <path d="M12 5v14M5 12h14" />,
    close: <path d="m6 6 12 12M6 18 18 6" />,
    grid: <><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></>,
    cube: <><path d="m12 3 9 5v8l-9 5-9-5V8l9-5Zm0 10L3 8m9 5 9-5m-9 5v8" /></>,
    pin: <><path d="m9 3 12 12-3 1-4-4-5 3-3-3 3-5-4-4h4ZM9 15l-6 6" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    chevron: <path d="m8 5 7 7-7 7" />,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5" /><path d="M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1" /></>,
    expand: <path d="M9 4H4v5m11-5h5v5M4 15v5h5m11-5v5h-5" />,
    layers: <><path d="m3 8 9-5 9 5-9 5-9-5Zm0 5 9 5 9-5M3 18l9 5 9-5" /></>
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}>{paths[name]}</svg>;
}

export function Loading({ text = "Loading the collection…" }: { text?: string }) {
  return <div className="loading-state" role="status"><span className="loading-orbit" aria-hidden="true" /><span>{text}</span></div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <div className="error-state" role="alert"><p>{message}</p><button className="button small" onClick={onRetry}><Icon name="refresh" size={14} />Try again</button></div>;
}
