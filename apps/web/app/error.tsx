"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return <main className="page-error"><p className="eyebrow">RGC / CATEGORY INTELLIGENCE</p><h1>The workspace could not load.</h1><p>Your collection is unchanged. Reload the workspace to try again.</p><button className="button primary" onClick={reset}>Reload workspace</button></main>;
}
