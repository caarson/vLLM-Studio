import { Circle, LoaderCircle, Triangle } from "lucide-react";
import React from "react";

interface Props {
  status: "running" | "starting" | "stopped" | "error";
}

const iconProps = {
  className: "w-4 h-4 text-white",
  strokeWidth: 1.5,
} as const;

export function StatusChip({ status }: Props) {
  const label = status.toUpperCase();
  let icon = <Circle {...iconProps} />;
  if (status === "starting") {
    icon = <LoaderCircle {...iconProps} className="w-4 h-4 text-white animate-spin" />;
  } else if (status === "error") {
    icon = <Triangle {...iconProps} />;
  }
  return (
    <span className="inline-flex items-center gap-2 px-3 py-1 text-xs tracking-[0.2em] uppercase border border-white/60 rounded-full">
      {icon}
      <span className="text-white">{label}</span>
    </span>
  );
}
