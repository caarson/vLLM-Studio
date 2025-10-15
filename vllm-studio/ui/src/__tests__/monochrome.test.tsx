import React from "react";
import { render } from "@testing-library/react";

import { MonoProgress } from "@/components/MonoProgress";
import { StatusChip } from "@/components/StatusChip";

function isMonochrome(value: string | null): boolean {
  if (!value || value === "" || value === "transparent") {
    return true;
  }
  const match = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/i);
  if (!match) {
    return false;
  }
  const [r, g, b] = match.slice(1, 4).map(Number);
  return r === g && g === b;
}

test("UI primitives stay monochrome", () => {
  const { container } = render(
    <div style={{ backgroundColor: "rgb(0,0,0)", color: "rgb(255,255,255)" }}>
      <MonoProgress value={63} />
      <StatusChip status="running" />
    </div>,
  );

  container.querySelectorAll("*").forEach((element) => {
    const styles = window.getComputedStyle(element);
    expect(isMonochrome(styles.color)).toBe(true);
    expect(isMonochrome(styles.backgroundColor)).toBe(true);
    const borderColor = styles.borderColor;
    if (borderColor && borderColor !== "") {
      expect(isMonochrome(borderColor)).toBe(true);
    }
  });
});
