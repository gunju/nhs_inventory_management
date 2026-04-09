import { PropsWithChildren } from "react";

export function Card({ children }: PropsWithChildren) {
  return <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm">{children}</section>;
}
