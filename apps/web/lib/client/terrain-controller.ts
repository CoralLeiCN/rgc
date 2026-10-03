/** Serializes renderer work. Orbit events only record the camera; they enqueue no geometry. */
export type TerrainOperation = "geometry" | "camera" | "appearance" | "selection" | "draft" | "gap" | "resize";
const priority: TerrainOperation[] = ["geometry", "camera", "appearance", "selection", "draft", "gap", "resize"];
export class TerrainRenderQueue {
  private pending = new Set<TerrainOperation>();
  private frame: number | null = null;
  private busy = false;
  private dragging = false;
  private disposed = false;
  constructor(private run: (operation: TerrainOperation) => Promise<void>, private request: (callback: () => void) => number, private cancel: (id: number) => void, private fail: (error: unknown) => void) {}
  invalidate(operation: TerrainOperation) { if (!this.disposed) { this.pending.add(operation); this.schedule(); } }
  setDragging(value: boolean) { this.dragging = value; if (!value) this.schedule(); }
  dispose() { this.disposed = true; this.pending.clear(); if (this.frame !== null) this.cancel(this.frame); this.frame = null; }
  private schedule() {
    if (this.disposed || this.dragging || this.busy || this.frame !== null || !this.pending.size) return;
    this.frame = this.request(() => { this.frame = null; void this.flush(); });
  }
  private async flush() {
    if (this.disposed || this.dragging || this.busy) return;
    const operation = priority.find(item => this.pending.has(item));
    if (!operation) return;
    this.pending.delete(operation);
    // A full render reads these values together. Updates arriving during its promise stay queued.
    if (operation === "geometry") for (const key of ["camera", "appearance", "selection", "draft", "gap"] as const) this.pending.delete(key);
    this.busy = true;
    try { await this.run(operation); } catch (error) { if (!this.disposed) this.fail(error); this.dispose(); }
    finally { this.busy = false; this.schedule(); }
  }
}
