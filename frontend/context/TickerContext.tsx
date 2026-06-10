"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

interface TickerContextType {
  globalTicker: string;
  setGlobalTicker: (ticker: string) => void;
}

const TickerContext = createContext<TickerContextType | undefined>(undefined);

export function TickerProvider({ children }: { children: React.ReactNode }) {
  const [globalTicker, setGlobalTickerState] = useState("");

  // Load from localStorage on mount
  useEffect(() => {
    const savedTicker = localStorage.getItem("astrocycle_global_ticker");
    if (savedTicker) {
      setGlobalTickerState(savedTicker);
    }
  }, []);

  const setGlobalTicker = (ticker: string) => {
    const upperTicker = ticker.toUpperCase().trim();
    setGlobalTickerState(upperTicker);
    localStorage.setItem("astrocycle_global_ticker", upperTicker);
  };

  return (
    <TickerContext.Provider value={{ globalTicker, setGlobalTicker }}>
      {children}
    </TickerContext.Provider>
  );
}

export function useTicker() {
  const context = useContext(TickerContext);
  if (context === undefined) {
    throw new Error("useTicker must be used within a TickerProvider");
  }
  return context;
}
