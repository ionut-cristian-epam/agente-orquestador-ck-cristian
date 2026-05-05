"use client";

import { useState, useEffect, useCallback } from "react";

export function useAccentColor() {
  const [accent, setAccentState] = useState<string>("blue");

  useEffect(() => {
    const stored = localStorage.getItem("accent-color") || "blue";
    setAccentState(stored);
    document.documentElement.setAttribute("data-accent", stored);
  }, []);

  const setAccent = useCallback((value: string) => {
    setAccentState(value);
    document.documentElement.setAttribute("data-accent", value);
    localStorage.setItem("accent-color", value);
  }, []);

  return [accent, setAccent] as const;
}
