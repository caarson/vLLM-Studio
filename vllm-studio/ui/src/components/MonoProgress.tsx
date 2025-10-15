import React from "react";

interface Props {
  value: number;
}

export function MonoProgress({ value }: Props) {
  const pct = Math.max(0, Math.min(100, value));
  const inProgress = pct < 100;
  return (
    <div className="w-full h-3 rounded-full bg-[#0d0d0d] border border-line-subtle overflow-hidden">
      <div
        className={inProgress ? "h-full animate-progress-move" : "h-full"}
        style={{
          width: `${pct}%`,
          background: "#fff",
          maskImage: inProgress ? "linear-gradient(135deg,#000 25%,transparent 25%)" : "none",
          WebkitMaskImage: inProgress ? "linear-gradient(135deg,#000 25%,transparent 25%)" : "none",
          maskSize: "12px 12px",
          WebkitMaskSize: "12px 12px",
        }}
      />
    </div>
  );
}
