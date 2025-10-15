import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#000000",
          surface: "#0a0a0a",
          card: "#111111",
        },
        line: {
          faint: "#1a1a1a",
          subtle: "#262626",
        },
        text: {
          primary: "#ffffff",
          secondary: "#cfcfcf",
          muted: "#9a9a9a",
        },
      },
      boxShadow: {
        panel: "0 0 0 1px #1f1f1f, 0 8px 24px rgba(0,0,0,1)",
      },
      keyframes: {
        move: {
          "0%": { maskPosition: "0 0" },
          "100%": { maskPosition: "12px 0" },
        },
      },
      animation: {
        "progress-move": "move 1s linear infinite",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
