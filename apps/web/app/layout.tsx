import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import "./families.css";
import "./family-navigator.css";
import "./price-distribution.css";
import "./analysis-panels.css";
import "./help-tip.css";
import "./product-configurator.css";
import "./terrain.css";

export const metadata: Metadata = {
  title: "Piece of Cake Pricing",
  description: "FMCG Pricing made easy. Explore prices, trait families, market gaps and brand positioning."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
