"use client";

import React from "react";
import { TickerProvider } from "../context/TickerContext";

export function Providers({ children }: { children: React.ReactNode }) {
  return <TickerProvider>{children}</TickerProvider>;
}
