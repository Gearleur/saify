import { createContext, useContext } from "react";
import type { DotTone } from "@/lib/domain";

export interface ToastInput {
  title: string;
  description?: string;
  tone?: DotTone;
}

export interface ToastContextValue {
  toast: (input: ToastInput) => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast doit être utilisé sous <ToastProvider>");
  return ctx;
}
