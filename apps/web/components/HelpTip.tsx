"use client";

import { useId, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { createPortal } from "react-dom";

interface Props {
  label: string; children: ReactNode; className?: string;
  triggerContent?: ReactNode; triggerClassName?: string; triggerStyle?: CSSProperties;
  pressed?: boolean; onTriggerClick?: () => void;
}
interface Position { left: number; top: number; maxWidth: number; maxHeight: number; ready: boolean; }

/** Explanatory content stays outside its trigger and any clipping panel containers. */
export function HelpTip({ label, children, className = "", triggerContent, triggerClassName, triggerStyle, pressed, onTriggerClick }: Props) {
  const tooltipId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const tooltip = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pinned = useRef(false);
  const pointerWithinTooltip = useRef(false);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<Position>({ left: 0, top: 0, maxWidth: 350, maxHeight: 420, ready: false });

  function clearCloseTimer() {
    if (closeTimer.current !== null) { clearTimeout(closeTimer.current); closeTimer.current = null; }
  }
  function close() {
    clearCloseTimer(); pinned.current = false; pointerWithinTooltip.current = false; setOpen(false);
  }
  function show() {
    clearCloseTimer(); setOpen(true);
  }
  function scheduleClose(force = false) {
    clearCloseTimer();
    if (!force && (pinned.current || document.activeElement === trigger.current)) return;
    closeTimer.current = setTimeout(close, 160);
  }

  useLayoutEffect(() => () => clearCloseTimer(), []);

  useLayoutEffect(() => {
    if (!open) return;
    let frame: number | null = null;
    const update = () => {
      if (!trigger.current || !tooltip.current) return;
      const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
      const viewportHeight = window.innerHeight;
      const maxWidth = Math.max(100, Math.min(350, viewportWidth - 24));
      const maxHeight = Math.max(80, Math.min(420, viewportHeight - 24));
      const anchor = trigger.current.getBoundingClientRect();
      const bounds = tooltip.current.getBoundingClientRect();
      const width = Math.min(bounds.width || maxWidth, maxWidth);
      const height = Math.min(bounds.height, maxHeight);
      const left = Math.max(12, Math.min(anchor.left + anchor.width / 2 - width / 2, viewportWidth - width - 12));
      const preferredTop = anchor.bottom + 9;
      const top = Math.max(12, Math.min(preferredTop + height <= viewportHeight - 12 ? preferredTop : anchor.top - height - 9, viewportHeight - height - 12));
      setPosition(current => current.ready && current.left === left && current.top === top && current.maxWidth === maxWidth && current.maxHeight === maxHeight ? current : { left, top, maxWidth, maxHeight, ready: true });
    };
    const schedulePosition = () => {
      if (frame !== null) cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => { frame = null; update(); });
    };
    const outside = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!trigger.current?.contains(target) && !tooltip.current?.contains(target)) close();
    };
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        if (document.activeElement && tooltip.current?.contains(document.activeElement)) trigger.current?.focus({ preventScroll: true });
        close();
      }
    };
    update();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(schedulePosition);
    if (tooltip.current) observer?.observe(tooltip.current);
    window.addEventListener("resize", schedulePosition);
    window.addEventListener("scroll", schedulePosition, true);
    document.addEventListener("pointerdown", outside, true);
    document.addEventListener("keydown", keyboard);
    return () => {
      if (frame !== null) cancelAnimationFrame(frame);
      observer?.disconnect(); clearCloseTimer();
      window.removeEventListener("resize", schedulePosition);
      window.removeEventListener("scroll", schedulePosition, true);
      document.removeEventListener("pointerdown", outside, true);
      document.removeEventListener("keydown", keyboard);
    };
  }, [open, children]);

  return <span className={`help-tip ${className}`}>
    <button ref={trigger} type="button" className={triggerClassName || "help-tip-trigger"} style={triggerStyle} aria-label={label} aria-expanded={open} aria-pressed={pressed} aria-controls={open ? tooltipId : undefined} aria-describedby={open ? tooltipId : undefined}
      onMouseEnter={show} onMouseLeave={() => scheduleClose()} onFocus={show}
      onBlur={event => {
        if (event.relatedTarget && tooltip.current?.contains(event.relatedTarget)) return;
        if (!event.relatedTarget && (pointerWithinTooltip.current || pinned.current)) return;
        pinned.current = false; scheduleClose(true);
      }}
      onClick={() => { if (pinned.current) close(); else { pinned.current = true; show(); } onTriggerClick?.(); }}>{triggerContent ?? <span aria-hidden="true">?</span>}</button>
    {open && typeof document !== "undefined" && createPortal(<div ref={tooltip} id={tooltipId} role="tooltip" className="help-tip-content" style={{ position: "fixed", left: position.left, top: position.top, maxWidth: position.maxWidth, maxHeight: position.maxHeight, visibility: position.ready ? "visible" : "hidden" }}
      onPointerEnter={() => { pointerWithinTooltip.current = true; clearCloseTimer(); }}
      onPointerLeave={() => { pointerWithinTooltip.current = false; scheduleClose(); }}
      onPointerDown={() => { pinned.current = true; clearCloseTimer(); }}
      onFocusCapture={clearCloseTimer}
      onBlurCapture={event => {
        if (event.relatedTarget && (tooltip.current?.contains(event.relatedTarget) || trigger.current?.contains(event.relatedTarget))) return;
        if (!event.relatedTarget && (pointerWithinTooltip.current || pinned.current)) return;
        pinned.current = false; scheduleClose(true);
      }}><span className="help-tip-label">{label}</span><div className="help-tip-body">{children}</div></div>, document.body)}
  </span>;
}
