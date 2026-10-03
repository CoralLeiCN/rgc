"use client";

export type Plotly = {
  react: (element: HTMLElement, traces: unknown[], layout: Record<string, unknown>, config: Record<string, unknown>) => Promise<unknown>;
  restyle: (element: HTMLElement, update: Record<string, unknown>, traces: number[]) => Promise<unknown>;
  relayout: (element: HTMLElement, layout: Record<string, unknown>) => Promise<unknown>;
  purge: (element: HTMLElement) => void;
  Plots: { resize: (element: HTMLElement) => Promise<unknown> };
};

declare global { interface Window { Plotly?: Plotly; } }
let plotlyPromise: Promise<Plotly> | null = null;

/** Load the local renderer once for active terrain views. */
export function loadPlotly() {
  if (window.Plotly) return Promise.resolve(window.Plotly);
  if (!plotlyPromise) plotlyPromise = new Promise<Plotly>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "/vendor/plotly-gl3d-3.1.0.min.js";
    script.async = true;
    script.onload = () => window.Plotly ? resolve(window.Plotly) : reject(new Error("The 3D renderer was unavailable."));
    script.onerror = () => { script.remove(); plotlyPromise = null; reject(new Error("The 3D renderer could not load.")); };
    document.head.appendChild(script);
  });
  return plotlyPromise;
}
